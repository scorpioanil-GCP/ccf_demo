#!/usr/bin/env python3
"""Wave 13a stage 1 — the REAL SIC cohort behind each memo-grade obligor.

    uv run generators/fetch_peer_cohorts.py --dry-run
    uv run generators/fetch_peer_cohorts.py

`credit-memo-context` §C calls peer thinness "the most natural, least contrived
source of real Context Debt in the catalog … it arises from the public data's
own coverage rather than from an engineered gap." That is true of `frames`, and
NOT true of what this estate currently holds, which is why this stage exists.

**What was wrong.** `loaders/load_xbrl_peers.py` draws its peer pool from Wave
0's screening set restricted to anchor SICs. A SIC absent from that screening
set therefore gets zero peers regardless of how many filers EDGAR actually has.
Measured 2026-08-22: 16 of 40 anchor SICs have no `peer_entity` row at all, and
943 of the 1,119 existing `(sic, tag, frame)` cohorts are "full" -- every
fetched peer tagged the concept -- so 84% of them measure OUR fetch scope and
say nothing whatever about `frames`. MASTEC's SIC 1623 reads 0 peers here and
has **32 real 10-K filers** at EDGAR. Presenting that 0 as peer thinness would
label our own gap `public`, which CLAUDE.md rule 1 exists to prevent.
Full reasoning: `docs/wave13a-design.md` §1.2.

**The denominator is the whole difficulty.** The full SIC cohort is not the
right expected size: SIC 2834 enumerates 1,903 filers, most of them shells that
filed once and dissolved. Benchmarking against that makes every obligor read
~99% thin -- a number that varies with nothing and would make a
`debt_tolerance` breach fire on every input. That is the Wave 12 defect shape
(known-issues.md §12): a gate whose inputs guarantee its verdict.

So this module measures thinness against an **active** denominator:

    expected(sic, frame)   = SIC cohort  ∩  filers reporting Assets in `frame`
    actual(sic, tag, frame)= SIC cohort  ∩  filers reporting `tag`  in `frame`
    thinness               = 1 - actual/expected

`Assets` is the liveness proxy: every operating company reports it, so the
expected set is "filers in this SIC that were alive and filing in this period".
What remains is concept-level tagging shortfall, which is exactly what §C
describes and exactly what the product should charge debt for.

The concept and period lists are IMPORTED from `loaders/load_xbrl_peers.py`
rather than restated, so the cohort denominators can never drift from the facts
Wave 2 actually loaded (known-issues.md §9.1 is that lesson).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date, timezone, datetime

import requests

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import REPO_ROOT, pg_connect
from ccf.fetch import (_MAX_ATTEMPTS, _RETRY_BACKOFF, _TRANSIENT_ERRORS,
                       SEC_LIMITER, get_json, sec_headers)
from loaders.load_xbrl_peers import FRAMES, FRAMES_WANTED, PEER_TAGS

SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave13a_peer_cohorts.json"

BROWSE = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&SIC={sic}"
          "&type=10-K&dateb=&owner=include&count=100&start={start}&output=atom")

#: Liveness proxy: a filer is "active in this period" if it reported ANY of
#: the tracked concepts in it.
#:
#: The first version of this used `Assets` alone, on the reasoning that every
#: operating company reports it. Running it disproved that in one line -- SIC
#: 8700 CY2023Q4I came back 3 filers reporting StockholdersEquity against 2
#: reporting Assets, i.e. **-50% thinness**, which is not a quantity. Some
#: filers report equity without tagging Assets. A single-concept denominator
#: cannot bound the numerator.
#:
#: The union does, by construction: actual(tag) is a subset of the union over
#: all tags, so thinness lands in [0, 1) for every cohort and no reading can be
#: negative. That property is asserted in `validators/memo_debt.py` rather than
#: assumed here.
BASELINE = "any tracked concept"

#: Hard stop on paging. SIC 2834 is the largest memo-grade cohort at 1,903;
#: this leaves headroom without letting a malformed response page forever.
PAGE_CAP = 4000


def memo_grade_sics() -> tuple[dict[str, list[str]], list[dict]]:
    """The SICs behind the 20 obligors with an extracted covenant.

    The memo-grade set is constrained to obligors carrying a covenant, because
    a covenant needs a filed credit agreement to anchor to and cannot be
    manufactured. `docs/wave13a-design.md` §5.
    """
    doc = json.loads((SCREEN / "covenants_extracted.json").read_text())
    leis = sorted({d["lei"] for d in doc["documents"]
                   if d.get("covenants") and d.get("lei")})
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, legal_name, sic FROM "{S}".legal_entity '
                    "WHERE lei = ANY(%s)", (leis,))
        rows = cur.fetchall()
    by_sic: dict[str, list[str]] = {}
    no_sic: list[dict] = []
    for lei, name, sic in rows:
        if sic:
            by_sic.setdefault(sic, []).append(lei)
        else:
            no_sic.append({"lei": lei, "legal_name": name})
    return by_sic, no_sic


def sic_cohort(sic: str) -> list[int]:
    """Every CIK EDGAR classifies under `sic` with a 10-K, paged to exhaustion."""
    seen: list[int] = []
    known: set[int] = set()
    start = 0
    while start < PAGE_CAP:
        # Same bounded, transient-only retry the rest of the estate uses. This
        # walks ~100 pages across 18 SICs; without it a single read timeout
        # aborts the whole enumeration, which is exactly what happened on the
        # first run. Constants imported, not restated, so one policy governs.
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            SEC_LIMITER.wait()
            try:
                resp = requests.get(BROWSE.format(sic=sic, start=start),
                                    headers=sec_headers(), timeout=45)
                resp.raise_for_status()
                break
            except _TRANSIENT_ERRORS as exc:  # noqa: PERF203
                if attempt == _MAX_ATTEMPTS:
                    raise
                wait_s = _RETRY_BACKOFF[attempt - 1]
                print(f"    [retry {attempt}/{_MAX_ATTEMPTS - 1}] SIC {sic} "
                      f"start={start}: {type(exc).__name__}, {wait_s}s")
                time.sleep(wait_s)
        got = [int(c) for c in re.findall(r"<cik>(\d+)</cik>", resp.text)]
        new = [c for c in got if c not in known]
        if not new:
            break
        known.update(new)
        seen.extend(new)
        if len(got) < 100:
            break
        start += 100
    return seen


def frame_for(tag: str, instant: bool, base: str) -> str:
    return f"{base}Q4I" if instant else base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    by_sic, no_sic = memo_grade_sics()
    print("Wave 13a — real SIC cohorts for the memo-grade set\n")
    print(f"  {sum(len(v) for v in by_sic.values())} obligors across "
          f"{len(by_sic)} SIC codes")
    for entry in no_sic:
        print(f"  [no SIC] {entry['legal_name']} ({entry['lei']}) — EDGAR "
              f"assigns none; no cohort is constructible")

    print("\nLeg 1 — enumerate each SIC cohort from EDGAR")
    cohorts: dict[str, list[int]] = {}
    for sic in sorted(by_sic):
        ciks = sic_cohort(sic)
        cohorts[sic] = ciks
        print(f"  SIC {sic:<6} {len(ciks):>5} filers   "
              f"({len(by_sic[sic])} memo-grade obligor(s))")

    print(f"\nLeg 2 — frames for {len(PEER_TAGS)} concepts x "
          f"{len(FRAMES_WANTED)} periods")
    # cik sets per (tag, frame), taken from the SAME frames payloads Wave 2 used
    reporters: dict[tuple[str, str], set[int]] = {}
    for tag, instant in PEER_TAGS:
        for base in FRAMES_WANTED:
            frame = frame_for(tag, instant, base)
            try:
                payload = get_json(FRAMES.format(tag=tag, frame=frame),
                                   is_sec=True, timeout=90)
            except Exception as exc:  # noqa: BLE001 — one concept failing is a
                # fact about that concept, not grounds to abort the sweep.
                print(f"  [skip] {tag} {frame}: {type(exc).__name__}")
                continue
            ciks = {e["cik"] for e in payload.get("data", []) if e.get("cik")}
            reporters[(tag, frame)] = ciks
            print(f"  {tag:<24}{frame:<10}{len(ciks):>7,} filers reporting")

    print("\nLeg 3 — cohort sizes, actual against an ACTIVE denominator")
    records = []
    for sic in sorted(cohorts):
        pool = set(cohorts[sic])
        for base in FRAMES_WANTED:
            # Active = reported ANY tracked concept in this period. Bounds
            # the numerator by construction; see BASELINE above.
            active: set[int] = set()
            for t, inst in PEER_TAGS:
                active |= reporters.get((t, frame_for(t, inst, base)), set())
            expected = len(pool & active)
            for tag, instant in PEER_TAGS:
                frame = frame_for(tag, instant, base)
                if (tag, frame) not in reporters:
                    continue
                actual = len(pool & reporters[(tag, frame)])
                records.append({
                    "sic": sic, "tag": tag, "frame": frame,
                    "sic_cohort_total": len(pool),
                    "expected_active": expected,
                    "actual": actual,
                    "thinness": round(1 - actual / expected, 4) if expected else None,
                })

    thin = [r for r in records if r["thinness"] is not None]
    if thin:
        worst = max(thin, key=lambda r: r["thinness"])
        best = min(thin, key=lambda r: r["thinness"])
        print(f"  {len(records)} (sic, tag, frame) cohorts")
        print(f"  thinnest  SIC {worst['sic']} {worst['tag']} {worst['frame']}: "
              f"{worst['actual']}/{worst['expected_active']} active "
              f"({worst['thinness']:.0%} short)")
        print(f"  fullest   SIC {best['sic']} {best['tag']} {best['frame']}: "
              f"{best['actual']}/{best['expected_active']} active "
              f"({best['thinness']:.0%} short)")
        rich = {r["sic"] for r in thin if r["expected_active"] >= 15}
        lean = {r["sic"] for r in thin if 0 < r["expected_active"] <= 3}
        print(f"\n  §F #4: SICs with an active cohort >= 15: {len(rich)}")
        print(f"          SICs with an active cohort <= 3:  {len(lean)}")

    if args.dry_run:
        print("\n  DRY RUN — artifact not written.")
        return 0

    ARTIFACT.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "SEC EDGAR browse-edgar SIC index + XBRL frames API",
        "baseline": BASELINE,
        "note": ("expected_active is the SIC cohort intersected with filers "
                 "reporting ANY tracked concept in that period -- a liveness "
                 "proxy, so thinness measures concept-level tagging shortfall "
                 "among filers that were actually filing, not company "
                 "mortality. The union (not one baseline concept) is what "
                 "bounds thinness to [0,1): a single-concept denominator "
                 "produced -50% on SIC 8700 CY2023Q4I."),
        "obligors_without_sic": no_sic,
        "sic_cohorts": {k: sorted(v) for k, v in cohorts.items()},
        "cohorts": records,
    }, indent=2) + "\n")
    print(f"\n  wrote {ARTIFACT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
