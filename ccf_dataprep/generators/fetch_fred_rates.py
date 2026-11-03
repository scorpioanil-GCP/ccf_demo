# generators/fetch_fred_rates.py
"""Fetch the twenty-one FRED series backing both Wave 12 products.

Design §1.4 measured all twenty-one live on 2026-08-21. The span matches
`benchmark_curve` (2024-01-02 onward) so the three rate tables share one
calendar rather than three.

FRED returns "." for a non-publication day (holiday, weekend). Those rows are
DROPPED, not carried forward -- a forward-filled rate is an invented
observation wearing a public provenance label.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ccf.currency import record_inputs                       # noqa: E402
from generators.fred_series import (                          # noqa: E402
    DERIVED_CROSSES, FX_SERIES, RATE_SERIES, SERIES,
    derive_cross, normalise_fx,
)

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
OBSERVATION_START = "2024-01-02"
OUT = Path(__file__).resolve().parent.parent / "sources" / "screening" / "wave12_rates.json"


def fetch_series(series_id: str, api_key: str) -> list[tuple[str, float]]:
    """Return [(obs_date, value)] with non-publication days dropped."""
    resp = requests.get(FRED_URL, timeout=30, params={
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": OBSERVATION_START,
    })
    resp.raise_for_status()
    body = resp.json()
    if "observations" not in body:
        raise RuntimeError(f"{series_id}: no observations key -- {body!r:.200}")
    out = []
    for o in body["observations"]:
        v = o["value"]
        if v == ".":            # FRED's non-publication marker
            continue
        out.append((o["date"], float(v)))
    if not out:
        raise RuntimeError(f"{series_id}: zero usable observations")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print("FRED_API_KEY not set", file=sys.stderr)
        return 2

    retrieved_at = datetime.now(timezone.utc).isoformat()
    rates, fx = [], []

    for sid in RATE_SERIES:
        obs = fetch_series(sid, api_key)
        for d, v in obs:
            rates.append({"series_id": sid, "obs_date": d, "value": v,
                          "unit": SERIES[sid].unit})
        print(f"  {sid:8s} {len(obs):5d} obs")
        time.sleep(0.4)

    by_series: dict[str, dict[str, float]] = {}
    for sid in FX_SERIES:
        obs = fetch_series(sid, api_key)
        by_series[sid] = dict(obs)
        for d, v in obs:
            pair, rate = normalise_fx(sid, v)
            fx.append({"pair": pair, "obs_date": d, "rate": rate,
                       "series_id": sid, "derivation": ""})
        print(f"  {sid:8s} {len(obs):5d} obs -> {normalise_fx(sid, obs[0][1])[0]}")
        time.sleep(0.4)

    # RULING F7 -- EUR/GBP is one of the six pairs and FRED does not publish it
    # (`DEXEUUK` does not exist). Derive it as a cross of two fetched legs,
    # on the dates where BOTH legs published. An inner join, never a
    # forward-fill: a cross built from one stale leg is a made-up rate.
    for pair, (base_sid, quote_sid) in DERIVED_CROSSES.items():
        base_obs, quote_obs = by_series[base_sid], by_series[quote_sid]
        shared = sorted(set(base_obs) & set(quote_obs))
        for d in shared:
            fx.append({
                "pair": pair, "obs_date": d,
                "rate": derive_cross(base_obs[d], quote_obs[d]),
                "series_id": f"{base_sid}/{quote_sid}",
                "derivation": f"({base_sid}) / ({quote_sid})",
            })
        dropped = len(set(base_obs) ^ set(quote_obs))
        print(f"  {pair:8s} {len(shared):5d} obs -> DERIVED "
              f"({dropped} dates dropped, only one leg published)")
        if not shared:
            raise RuntimeError(f"{pair}: the two legs share no dates")

    artifact = {
        "_meta": {"retrieved_at": retrieved_at,
                  "observation_start": OBSERVATION_START,
                  "source": "FRED (Federal Reserve Bank of St. Louis)"},
        "_inputs": record_inputs(),
        "rates": rates,
        "fx": fx,
    }
    print(f"\n  {len(rates)} rate observations, {len(fx)} fx observations")
    if args.dry_run:
        print("  --dry-run: not written")
        return 0
    OUT.write_text(json.dumps(artifact, indent=1))
    print(f"  wrote {OUT.relative_to(Path.cwd())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
