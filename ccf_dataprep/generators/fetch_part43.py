# generators/fetch_part43.py
"""Fetch ten days of CFTC Part 43 public swap-reporting data from DTCC.

Design §1.5/§1.6 -- the FX shaping distributions for Wave 12's reconciliation
product must be patterned on real market timing and pair mix, not invented.
DTCC's cumulative daily FOREX file carries every publicly disseminated FX
swap; `generators/part43.py::derive_profile` filters it to the six G10 pairs
and derives the shaping distributions from those rows only.

`known-issues.md` §8.1 -- a 200 response is not proof of a usable body. That
incident was EDGAR serving an HTML rendering where XML was expected; the
equivalent failure here would be a 200 whose bytes are not a valid zip, or a
zip that unzips to zero G10 rows. Both are read from the actual bytes, never
inferred from the status code alone.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ccf.currency import record_inputs                        # noqa: E402
from generators.part43 import G10_PAIRS, derive_profile        # noqa: E402

URL_TMPL = ("https://pddata.dtcc.com/ppd/api/report/cumulative/cftc/"
            "CFTC_CUMULATIVE_FOREX_{day}.zip")

CACHE_DIR = Path(__file__).resolve().parent.parent / "sources" / "part43"
OUT = Path(__file__).resolve().parent.parent / "sources" / "screening" / "wave12_part43_profile.json"

END_DATE = datetime(2026, 8, 19, tzinfo=timezone.utc).date()
N_DAYS = 10
MIN_MERGED_ROWS = 10_000


def last_n_weekdays(end: "datetime.date", n: int) -> list:
    """The n most recent weekdays (Mon-Fri) ending on and including `end`."""
    days = []
    d = end
    while len(days) < n:
        if d.weekday() < 5:          # 0=Mon .. 4=Fri
            days.append(d)
        d -= timedelta(days=1)
    return list(reversed(days))


def fetch_day_bytes(day: "datetime.date") -> bytes | None:
    """Cached zip bytes for one day, or None if the day is unavailable.

    Caches to disk first, THEN reads back from disk -- so a cached file and
    a freshly-fetched one go through the identical "are these usable bytes"
    check, and a re-run never re-downloads a day already on disk.
    """
    tag = day.strftime("%Y_%m_%d")
    cache_path = CACHE_DIR / f"CFTC_CUMULATIVE_FOREX_{tag}.zip"

    if not cache_path.exists():
        url = URL_TMPL.format(day=tag)
        try:
            resp = requests.get(url, timeout=60)
        except requests.RequestException as e:
            print(f"  {tag}: request failed -- {e}")
            return None
        if resp.status_code != 200 or not resp.content:
            print(f"  {tag}: HTTP {resp.status_code}, {len(resp.content)} bytes -- skipped")
            return None
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(resp.content)

    return cache_path.read_bytes()


def rows_from_zip(data: bytes, tag: str) -> list[dict] | None:
    """Read the bytes, not the status: a bad or empty zip is a skip, not a crash."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            print(f"  {tag}: zip has no CSV member -- skipped")
            return None
        with zf.open(names[0]) as fh:
            text = io.TextIOWrapper(fh, encoding="utf-8", errors="replace")
            rows = list(csv.DictReader(text))
    except zipfile.BadZipFile:
        print(f"  {tag}: not a valid zip (200 with wrong content) -- skipped")
        return None
    if not rows:
        print(f"  {tag}: zip unzipped to zero rows -- skipped")
        return None
    return rows


def merge_profiles(profiles: list[dict]) -> dict:
    """Sum the per-day `derive_profile` counters into one merged profile."""
    from collections import Counter

    n_rows = 0
    pair_mix: Counter = Counter()
    hour_mix: Counter = Counter()
    action_mix: Counter = Counter()
    chain_lengths: Counter = Counter()

    for p in profiles:
        n_rows += p["n_rows"]
        pair_mix.update(p["pair_mix"])
        hour_mix.update(p["hour_mix"])
        action_mix.update(p["action_mix"])
        chain_lengths.update(p["chain_lengths"])

    return {
        "n_rows": n_rows,
        "pair_mix": dict(pair_mix),
        "hour_mix": dict(hour_mix),
        "action_mix": dict(action_mix),
        "chain_lengths": dict(chain_lengths),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    retrieved_at = datetime.now(timezone.utc).isoformat()
    days = last_n_weekdays(END_DATE, N_DAYS)

    profiles = []
    days_read = []
    skipped = []

    for day in days:
        tag = day.strftime("%Y-%m-%d")
        data = fetch_day_bytes(day)
        if data is None:
            skipped.append({"day": tag, "reason": "fetch failed (non-200 or empty body)"})
            continue
        rows = rows_from_zip(data, tag)
        if rows is None:
            skipped.append({"day": tag, "reason": "unusable bytes (bad zip or zero rows)"})
            continue
        total_rows = len(rows)
        profile = derive_profile(rows)
        print(f"  {tag}: {total_rows:6d} total rows, {profile['n_rows']:5d} G10 rows")
        profiles.append(profile)
        days_read.append(tag)

    if not profiles:
        print("no days produced usable data -- aborting", file=sys.stderr)
        return 2

    merged = merge_profiles(profiles)
    print(f"\n  merged: {merged['n_rows']} G10 rows across {len(days_read)} day(s), "
          f"{len(skipped)} skipped")

    if merged["n_rows"] < MIN_MERGED_ROWS:
        print(f"FAIL: merged n_rows {merged['n_rows']} < {MIN_MERGED_ROWS} -- "
              f"the G10 filter or the source shape may have changed. Not writing.",
              file=sys.stderr)
        return 1

    artifact = {
        **merged,
        "_meta": {
            "retrieved_at": retrieved_at,
            "days": days_read,
            "skipped": skipped,
            "source": "DTCC CFTC Part 43 cumulative FOREX (pddata.dtcc.com)",
        },
        "_inputs": record_inputs(),
    }

    if args.dry_run:
        print("  --dry-run: not written")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, indent=1))
    print(f"  wrote {OUT.relative_to(Path.cwd())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
