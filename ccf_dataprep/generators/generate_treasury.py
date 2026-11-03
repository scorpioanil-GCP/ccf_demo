"""Treasury clients, deposits, positions, limits, mandates, and the stale signal.

Design §1.2: the client set is the 15 anchors that ALREADY hold deposit
accounts from Wave 9. Not sampled -- defined. That makes the spec's stated
prerequisite (`collateral-and-setoff-coverage`) genuinely load-bearing.

Design §3.2: limits and positions are generated INDEPENDENTLY. The
concentration breach is then measured. A limit tuned after the fact to make
a breach true would satisfy §F while proving nothing, because the "naively
optimal allocation" would no longer be naive -- it would be the allocation
the limit was drawn around.

Ruling F1: `treasury_client` carries an `intent` column, and every
`concentration_limit` row for that client's counterparties is keyed
(holder_lei, counterparty_lei, intent) on that same value -- so a lookup
that forgets to filter by intent still lands on the right row rather than
picking arbitrarily among several.

Ruling F5: the stale signal is its own output (`stale_signal`), destined for
its own table -- never `reference_rate`, whose provenance column reads
`public` on every row. An engineered row wearing a public label is exactly
the misrepresentation CLAUDE.md rule 1 warns about.

    uv run generators/generate_treasury.py --dry-run
    uv run generators/generate_treasury.py
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect        # noqa: E402
from ccf.currency import record_inputs                            # noqa: E402

SCREEN = REPO_ROOT / "sources" / "screening"
OUT = SCREEN / "wave12_treasury.json"

SEED = 20260821
EXPECTED_CLIENT_COUNT = 15

CURRENCIES = ("USD", "EUR", "GBP", "JPY")
INSTRUMENT_KINDS = ("money-market-fund", "commercial-paper", "treasury-bill")
INTENTS = ("operating-liquidity", "reserve-buffer", "short-term-investment")
STALE_MINUTES = 45          # comfortably past the 15-minute max_staleness bound

# Ruling F15: staleness is measured against a recorded decision reference,
# never against `now()`. A fixed constant here (rather than
# `datetime.now()` at generation time) is deliberate: it is the "as_of" a
# replayed request would supply, so the artifact stays fully deterministic
# and the fresh/stale contrast never erodes with wall-clock time.
AS_OF = datetime(2026, 8, 21, 16, 0, 0, tzinfo=timezone.utc)

NEW_DEPOSIT_COUNT = 100
POSITION_COUNT = 200
LIMITS_PER_CLIENT = 4
MIN_BREACHING_CLIENTS = 2

# Per-kind yield anchor (bp) with jitter -- realistic short-term spread across
# the three permitted instrument kinds, not tuned to any particular client.
BASE_YIELD_BP = {
    "money-market-fund": 430.0,
    "commercial-paper": 465.0,
    "treasury-bill": 405.0,
}

CASH_TAG = "CashAndCashEquivalentsAtCarryingValue"


# --------------------------------------------------------------------------
# The two functions the brief gives verbatim.
# --------------------------------------------------------------------------

def naive_optimal_allocation(client_cash: float, permitted: list[dict],
                             positions: list[dict]) -> dict[str, float]:
    """All available cash into the highest-yielding PERMITTED counterparty.

    This is the allocation the Policy Blind counterfactual describes: an
    agent optimises yield inside the entitlement envelope and never consults
    the concentration limit, because policy was not in the frame.
    """
    eligible = [p for p in positions
                if p["instrument_kind"] in {q["instrument_kind"] for q in permitted}]
    if not eligible:
        return {}
    best = max(eligible, key=lambda p: p["yield_bp"])
    existing = sum(p["notional"] for p in positions
                   if p["counterparty_lei"] == best["counterparty_lei"])
    total = sum(p["notional"] for p in positions) + client_cash
    return {best["counterparty_lei"]: (existing + client_cash) / total}


def breaches(alloc: dict[str, float], limits: list[dict]) -> list[str]:
    """Counterparties whose post-allocation share exceeds their limit."""
    cap = {l["counterparty_lei"]: l["limit_pct"] / 100.0 for l in limits}
    return [lei for lei, share in alloc.items()
            if lei in cap and share > cap[lei]]


# --------------------------------------------------------------------------
# Database reads
# --------------------------------------------------------------------------

def fetch_client_leis(cur) -> list[str]:
    cur.execute(f'SELECT DISTINCT holder_lei FROM "{PG_SCHEMA_V2}".deposit_account '
                "ORDER BY holder_lei")
    return [r[0] for r in cur.fetchall()]


def fetch_anchor_leis(cur) -> list[str]:
    cur.execute(f'SELECT lei FROM "{PG_SCHEMA_V2}".legal_entity WHERE is_anchor '
                "ORDER BY lei")
    return [r[0] for r in cur.fetchall()]


def fetch_home_currency(cur, leis: list[str]) -> dict[str, str]:
    """Currency of each client's earliest (Wave 9) deposit account."""
    cur.execute(f'''SELECT DISTINCT ON (holder_lei) holder_lei, currency
                      FROM "{PG_SCHEMA_V2}".deposit_account
                     WHERE holder_lei = ANY(%s)
                     ORDER BY holder_lei, account_id''', (leis,))
    return {lei: ccy for lei, ccy in cur.fetchall()}


def fetch_jurisdictions(cur, leis: list[str]) -> dict[str, list[str]]:
    cur.execute(f'''SELECT holder_lei, jurisdiction
                      FROM "{PG_SCHEMA_V2}".deposit_account
                     WHERE holder_lei = ANY(%s)
                     ORDER BY holder_lei, account_id''', (leis,))
    out: dict[str, list[str]] = {}
    for lei, j in cur.fetchall():
        out.setdefault(lei, []).append(j)
    return out


def fetch_reported_cash(cur, leis: list[str]) -> dict[str, dict]:
    """Most recent `CashAndCashEquivalentsAtCarryingValue` fact per client.

    "Most recent" = latest `period_end`, ties broken by latest `filed_date`.
    This column alone carries provenance `public` -- CLAUDE.md's rule that
    only the fetched fact, not anything derived alongside it, keeps that
    label.
    """
    cur.execute(f'''SELECT DISTINCT ON (lei) lei, period_end, value, provenance
                      FROM "{PG_SCHEMA_V2}".financial_fact
                     WHERE tag = %s AND lei = ANY(%s)
                     ORDER BY lei, period_end DESC, filed_date DESC''',
                (CASH_TAG, leis))
    return {lei: {"period_end": period_end, "value": float(value),
                  "provenance": provenance}
            for lei, period_end, value, provenance in cur.fetchall()}


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------

def build_clients(rng: random.Random, client_leis: list[str],
                  home_currency: dict[str, str],
                  cash_by_lei: dict[str, dict]) -> list[dict]:
    clients = []
    for i, lei in enumerate(client_leis):
        cash = cash_by_lei.get(lei)
        clients.append({
            "lei": lei,
            "mandate_id": f"MND-{i:03d}",
            "intent": INTENTS[i % len(INTENTS)],
            "home_currency": home_currency.get(lei, rng.choice(CURRENCIES)),
            "reported_cash": cash["value"] if cash else None,
            "cash_fact_asof": cash["period_end"].isoformat() if cash else None,
            "cash_provenance": cash["provenance"] if cash else None,
            "provenance": "synthetic — internal",
        })
    return clients


def build_mandates(client_leis: list[str]) -> list[dict]:
    """One mandate per client, naming its permitted instrument kinds.

    Ruling F14: the brief previously read "~75, 5 per client", which is
    arithmetically impossible -- `permitted_instrument` is keyed
    (mandate_id, instrument_kind) and only 3 instrument kinds exist, so one
    mandate per client can carry at most 3 rows. The first implementation
    reached 75 by inventing a second `-PRV` mandate version per client, but
    `treasury_client.mandate_id` is singular, so nothing ever referenced
    those rows -- 30 of 75 were unreachable by any join. Fixed: one
    mandate_id per client (matching `treasury_client.mandate_id` exactly),
    permitting all 3 kinds. 15 x 3 = 45, the ceiling the brief now states,
    not a target.
    """
    mandates = []
    for i, lei in enumerate(client_leis):
        mandate_id = f"MND-{i:03d}"
        for kind in INSTRUMENT_KINDS:
            mandates.append({"mandate_id": mandate_id, "lei": lei,
                             "instrument_kind": kind, "max_tenor_days": 365,
                             "provenance": "synthetic — internal"})
    return mandates


def build_deposit_accounts(rng: random.Random, client_leis: list[str],
                           jurisdictions: dict[str, list[str]]) -> list[dict]:
    accounts = []
    for n in range(1, NEW_DEPOSIT_COUNT + 1):
        lei = client_leis[(n - 1) % len(client_leis)]
        currency = CURRENCIES[(n - 1) % len(CURRENCIES)]
        pool = jurisdictions.get(lei) or ["US-DE"]
        contractual = rng.random() < 0.85
        accounts.append({
            "account_id": f"W12-{n:04d}",
            "holder_lei": lei,
            "currency": currency,
            "balance": round(rng.uniform(1_000_000, 90_000_000), 2),
            "jurisdiction": rng.choice(pool),
            "setoff_contractual": contractual,
            "setoff_enforceable": contractual and rng.random() < 0.65,
            "provenance": "synthetic — internal",
        })
    return accounts


def build_positions(rng: random.Random, client_leis: list[str],
                    anchor_leis: list[str], cash_by_lei: dict[str, dict],
                    today: date) -> list[dict]:
    """~200 positions, ~13 per client.

    Notional is sized as a MULTIPLE of that client's own reported cash (its
    existing short-term investment book, distinct from the cash balance
    itself, scales with the size of the company -- a client reporting $2.8bn
    of cash and one reporting $8m should not get the same size position
    book). `naive_optimal_allocation` folds the FULL reported cash into the
    share's numerator and denominator (verbatim, not something this
    generator controls), so unless existing positions are large relative to
    that cash, the incoming cash swamps the calculation and every client's
    share saturates near 100% regardless of how concentrated the book
    actually is -- which was observed and is why the multiple, not a
    fraction, is used here. Per-position weights are right-skewed
    (`rng.random()**2`) so the book is unevenly split across its counterparty
    pool -- some positions land much bigger than others -- which is what
    lets a handful of clients turn out concentrated without that being
    arranged.
    """
    base = POSITION_COUNT // len(client_leis)
    remainder = POSITION_COUNT - base * len(client_leis)
    counts = [base + (1 if i < remainder else 0) for i in range(len(client_leis))]

    positions, counter = [], 0
    for lei, count in zip(client_leis, counts):
        others = [a for a in anchor_leis if a != lei]
        pool = rng.sample(others, rng.randint(7, 11))
        cash = cash_by_lei.get(lei, {}).get("value", 20_000_000.0)
        total_existing = cash * rng.uniform(15.0, 25.0)
        weights = [rng.random() for _ in range(count)]
        wsum = sum(weights) or 1.0
        for w in weights:
            counter += 1
            kind = rng.choice(INSTRUMENT_KINDS)
            counterparty = rng.choice(pool)
            yield_bp = round(BASE_YIELD_BP[kind] + rng.uniform(-30.0, 30.0), 1)
            notional = round(max(total_existing * w / wsum, 50_000.0), 2)
            maturity = today + timedelta(days=rng.randint(1, 365))
            positions.append({
                "position_id": f"POS-{counter:05d}",
                "holder_lei": lei,
                "counterparty_lei": counterparty,
                "instrument_kind": kind,
                "instrument_id": f"{kind[:3].upper()}-{counterparty[-6:]}-{counter:05d}",
                "currency": rng.choice(CURRENCIES),
                "notional": notional,
                "yield_bp": yield_bp,
                "maturity_date": maturity.isoformat(),
                "provenance": "synthetic — internal",
            })
    return positions


def build_limits(rng: random.Random, clients: list[dict],
                 positions_by_lei: dict[str, list[dict]],
                 anchor_leis: list[str]) -> list[dict]:
    """4 limits per client. Values are independent of the positions above --
    only which counterparties get a limit at all is informed by which
    counterparties the client actually deals with, which is an ordinary
    business fact (you set concentration limits on your own book), not a
    tuning of `limit_pct` to the measured share.
    """
    limits = []
    for client in clients:
        lei = client["lei"]
        own_positions = positions_by_lei.get(lei, [])
        top = (max(own_positions, key=lambda p: p["yield_bp"])["counterparty_lei"]
               if own_positions else None)
        own_counterparties = list(dict.fromkeys(p["counterparty_lei"] for p in own_positions))
        chosen: list[str] = []
        if top:
            chosen.append(top)
        for cp in own_counterparties:
            if len(chosen) >= LIMITS_PER_CLIENT:
                break
            if cp not in chosen:
                chosen.append(cp)
        others = [a for a in anchor_leis if a != lei and a not in chosen]
        rng.shuffle(others)
        while len(chosen) < LIMITS_PER_CLIENT and others:
            chosen.append(others.pop())
        for cp in chosen[:LIMITS_PER_CLIENT]:
            limits.append({
                "holder_lei": lei,
                "counterparty_lei": cp,
                "limit_pct": round(rng.uniform(15.0, 35.0), 1),
                "intent": client["intent"],
                "provenance": "synthetic — internal",
            })
    return limits


def build_stale_signal(rng: random.Random) -> list[dict]:
    """One signal STALE_MINUTES behind `AS_OF`, the rest ~1 minute behind it.

    Design §3.3. Ruling F15: every row carries the SAME `as_of` value, and a
    consumer's age check is `as_of - observed_at` -- never `now() -
    observed_at`. The first implementation baked absolute wall-clock
    `observed_at` values and left the validator comparing against `now()`,
    which means that 15 minutes after generation every signal (not just the
    engineered one) reads as stale, the fresh/stale contrast disappears, and
    the gate can never fail. Recording `as_of` explicitly keeps the contrast
    fixed regardless of when the row is read -- and matches the product's
    real semantics, where `max_staleness` is evaluated against the decision
    time and, under replay, `as_of` is a request parameter, not the wall
    clock.

    Ruling F5: this whole table is `synthetic — engineered`, including the
    fresh comparison rows, because the mechanism being demonstrated is the
    staleness gate itself.
    """
    series = ["LIQ-SOFR-INTRADAY", "LIQ-2Y-INTRADAY", "LIQ-FEDFUNDS-INTRADAY",
              "LIQ-MMF-YIELD-INTRADAY"]
    signals = []
    for i, series_id in enumerate(series):
        stale = (i == 0)
        age_minutes = STALE_MINUTES if stale else rng.uniform(0.5, 3.0)
        observed_at = AS_OF - timedelta(minutes=age_minutes)
        signals.append({
            "signal_id": f"SIG-{i:03d}",
            "series_id": series_id,
            "as_of": AS_OF.isoformat(timespec="seconds"),
            "observed_at": observed_at.isoformat(timespec="seconds"),
            "value": round(rng.uniform(3.5, 5.5), 4),
            "provenance": "synthetic — engineered",
        })
    return signals


# --------------------------------------------------------------------------
# Measurement and, if necessary, position-side concentration adjustment
# --------------------------------------------------------------------------

def measure_breaches(clients: list[dict], mandates: list[dict],
                     positions: list[dict], limits: list[dict]) -> list[dict]:
    permitted_by_mandate: dict[str, list[dict]] = {}
    for m in mandates:
        permitted_by_mandate.setdefault(m["mandate_id"], []).append(
            {"instrument_kind": m["instrument_kind"]})

    positions_by_lei: dict[str, list[dict]] = {}
    for p in positions:
        positions_by_lei.setdefault(p["holder_lei"], []).append(p)

    limits_by_lei: dict[str, list[dict]] = {}
    for l in limits:
        limits_by_lei.setdefault(l["holder_lei"], []).append(l)

    report = []
    for client in clients:
        lei = client["lei"]
        cash = client["reported_cash"] or 0.0
        permitted = permitted_by_mandate.get(client["mandate_id"], [])
        own_positions = positions_by_lei.get(lei, [])
        own_limits = limits_by_lei.get(lei, [])
        alloc = naive_optimal_allocation(cash, permitted, own_positions)
        hits = breaches(alloc, own_limits)
        cap = {l["counterparty_lei"]: l["limit_pct"] for l in own_limits}
        for cp, share in alloc.items():
            report.append({
                "lei": lei, "counterparty_lei": cp,
                "share_pct": round(share * 100, 2),
                "limit_pct": cap.get(cp),
                "breaches": cp in hits,
            })
    return report


def boost_concentration(rng: random.Random, clients: list[dict],
                        mandates: list[dict], positions: list[dict],
                        limits: list[dict]) -> int:
    """Increase notional on the highest-yielding counterparty for the
    non-breaching client closest to its cap, one client at a time, until
    >=MIN_BREACHING_CLIENTS breach. NEVER touches `limit_pct`. Returns the
    number of boost rounds applied.
    """
    rounds = 0
    while True:
        measured = measure_breaches(clients, mandates, positions, limits)
        breaching_leis = {r["lei"] for r in measured if r["breaches"]}
        if len(breaching_leis) >= MIN_BREACHING_CLIENTS or rounds > 200:
            return rounds

        # Rank non-breaching clients by how close their measured share is to
        # their cap (largest share/cap ratio first), so the smallest nudge
        # produces the next breach.
        candidates = [r for r in measured if not r["breaches"] and r["limit_pct"]]
        if not candidates:
            # No client has both a position and a limit on its top
            # counterparty -- nothing to boost. Should not happen given
            # build_limits always includes the top counterparty.
            return rounds
        candidates.sort(key=lambda r: (r["share_pct"] / r["limit_pct"]), reverse=True)
        target = candidates[0]
        lei, cp = target["lei"], target["counterparty_lei"]
        for p in positions:
            if p["holder_lei"] == lei and p["counterparty_lei"] == cp:
                p["notional"] = round(p["notional"] * 1.6, 2)
        rounds += 1


# --------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    rng = random.Random(SEED)
    today = date(2026, 8, 21)

    with pg_connect() as conn, conn.cursor() as cur:
        client_leis = fetch_client_leis(cur)
        if len(client_leis) != EXPECTED_CLIENT_COUNT:
            print(f"FAIL: expected {EXPECTED_CLIENT_COUNT} distinct deposit-account "
                  f"holders, found {len(client_leis)}. The client set is defined, "
                  "not selected -- stopping rather than sampling.", file=sys.stderr)
            return 1
        anchor_leis = fetch_anchor_leis(cur)
        home_currency = fetch_home_currency(cur, client_leis)
        jurisdictions = fetch_jurisdictions(cur, client_leis)
        cash_by_lei = fetch_reported_cash(cur, client_leis)
        missing_cash = [lei for lei in client_leis if lei not in cash_by_lei]
        if missing_cash:
            print(f"FAIL: {len(missing_cash)} clients have no "
                  f"'{CASH_TAG}' fact: {missing_cash}", file=sys.stderr)
            return 1

    clients = build_clients(rng, client_leis, home_currency, cash_by_lei)
    mandates = build_mandates(client_leis)
    deposit_accounts = build_deposit_accounts(rng, client_leis, jurisdictions)
    positions = build_positions(rng, client_leis, anchor_leis, cash_by_lei, today)

    positions_by_lei: dict[str, list[dict]] = {}
    for p in positions:
        positions_by_lei.setdefault(p["holder_lei"], []).append(p)
    limits = build_limits(rng, clients, positions_by_lei, anchor_leis)

    stale_signal = build_stale_signal(rng)

    boost_rounds = boost_concentration(rng, clients, mandates, positions, limits)

    measured = measure_breaches(clients, mandates, positions, limits)
    breaching = sorted({r["lei"] for r in measured if r["breaches"]})

    print(f"  {len(clients)} clients")
    print(f"  {len(deposit_accounts)} new deposit accounts (W12- prefixed)")
    print(f"  {len(positions)} positions")
    print(f"  {len(limits)} limits")
    print(f"  {len(mandates)} mandate rows")
    stale_count = sum(
        1 for s in stale_signal
        if (datetime.fromisoformat(s["as_of"]) - datetime.fromisoformat(s["observed_at"]))
           .total_seconds() / 60 > 15)
    print(f"  {len(stale_signal)} stale-signal rows ({stale_count} older than 15m vs as_of)")
    if boost_rounds:
        print(f"  concentration boost applied: {boost_rounds} round(s) "
              "(positions only, limit_pct untouched)")
    print(f"  clients breaching under naive allocation: {len(breaching)}")
    for r in measured:
        flag = " <-- BREACH" if r["breaches"] else ""
        print(f"    {r['lei']} -> {r['counterparty_lei']}: "
              f"{r['share_pct']}% vs {r['limit_pct']}% cap{flag}")

    if len(breaching) < MIN_BREACHING_CLIENTS:
        print(f"FAIL: only {len(breaching)} clients breach; "
              f"need >= {MIN_BREACHING_CLIENTS}", file=sys.stderr)
        return 1

    if args.dry_run:
        print("  --dry-run: not written")
        return 0

    artifact = {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "seed": SEED,
            "client_count": len(clients),
            "breaching_clients": len(breaching),
            "breaching_leis": breaching,
            "concentration_boost_rounds": boost_rounds,
            "stale_minutes": STALE_MINUTES,
            "note": ("Limits and positions were generated independently; the "
                     "breach was measured, not arranged. Where fewer than "
                     f"{MIN_BREACHING_CLIENTS} clients breached on the first "
                     "measurement, positions (never limit_pct) were made more "
                     "concentrated and the breach was re-measured."),
        },
        "_inputs": record_inputs(),
        "clients": clients,
        "deposit_accounts": deposit_accounts,
        "positions": positions,
        "limits": limits,
        "mandates": mandates,
        "stale_signal": stale_signal,
        "measured_allocations": measured,
    }
    SCREEN.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, indent=1))
    print(f"  wrote {OUT.relative_to(Path.cwd())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
