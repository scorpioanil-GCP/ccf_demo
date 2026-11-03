#!/usr/bin/env python3
"""Institutional holders of the anchors, from one quarterly 13F dataset.

The SEC's dataset naming CHANGED: the old `<YYYY>q<N>_form13f.zip` pattern 404s
for recent periods. Current form is a date range, e.g.
`01mar2026-31may2026_form13f.zip` (~99 MB).

Issuer matching is fuzzy — `NAMEOFISSUER` against our legal names — so every row
carries a band. §C asks for 13F as context only, so an imperfect match degrades
gracefully rather than corrupting a join.

**`manager_cik` comes from `SUBMISSION.tsv`'s `CIK` column, not from the
accession-number prefix.** An earlier version of this script derived
`manager_cik = ACCESSION_NUMBER.split("-")[0]` — that prefix identifies the
*filing agent*, not the manager. One agent files for hundreds of managers
(5,376 of 11,761 submissions in this period have agent prefix != real CIK),
so deriving identity from it collapsed distinct institutions into one row:
`institutional_holder` then silently erased ~5,357 institution-issuer
relationships in the one table whose entire purpose is which institutions
hold which issuer, while looking complete because every row still had *some*
CIK-shaped value in it.

**Amendments are resolved before aggregation, not folded with MAX/SUM at
load time.** `SUBMISSION.tsv` gives `SUBMISSIONTYPE` (`13F-HR` original vs
`13F-HR/A` amendment) and `FILING_DATE` per accession. Grouped by
`(CIK, PERIODOFREPORT)`: if any amendment exists for that manager/period, the
latest one by `FILING_DATE` wins and every original (and earlier amendment)
it restates is discarded entirely — a 13F amendment restates a position, it
does not add to it. 166 of 11,591 (cik, period) groups in this period carry
more than one accession, and every one of those 166 involves an amendment
(none are duplicate un-amended originals) — 33 have more than one amendment,
resolved by latest `FILING_DATE` **parsed as a date** via `_filing_date()`,
not compared as the raw `DD-MON-YYYY` string — a raw-string comparison sorts
by day-of-month, then month NAME alphabetically, then year, so
"13-APR-2026" < "13-MAR-2026" and a December/January amendment pair would
never reach the year at all. See `_filing_date()`'s docstring.

**Within the single winning accession, line items for the same issuer are
summed**, not deduplicated or maxed. A manager can report one CUSIP across
several INFOTABLE rows in the same filing — investment-discretion splits,
multiple accounts — and those really are separate slices of one position, so
summing them (never across accessions, only within the one winning one)
recovers the manager's actual reported total with no double-count.

    uv run generators/fetch_13f.py --dry-run
    uv run generators/fetch_13f.py --period 01mar2026-31may2026
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.fetch import SourceManifest, fetch
from generators.form4 import STATE_SUFFIX
from generators.persons import match_score

SCREEN = REPO_ROOT / "sources" / "screening"
BASE = "https://www.sec.gov/files/structureddata/data/form-13f-data-sets"
STRONG, WEAK = 0.92, 0.80


def _norm_issuer(name: str) -> str:
    # known-issues.md §8: EDGAR's trailing `/XX/` state-of-incorporation
    # suffix (e.g. "AMPHENOL CORP /DE/") was previously left in place, so
    # "de" survived tokenizing as if it were part of the name and the issuer
    # never matched its own anchor at a "strong" band. Same root cause as the
    # owner_kind defect (§8.5) -- strip it with the SAME regex form4.py
    # exports, rather than a second private copy.
    name = STATE_SUFFIX.sub("", name)
    drop = {"inc", "inc.", "corp", "corp.", "corporation", "co", "co.", "the",
            "lp", "l.p.", "llc", "plc", "ltd", "holdings", "group", "trust"}
    tokens = [t for t in "".join(
        c if c.isalnum() or c.isspace() else " " for c in name.lower()).split()
        if t not in drop]
    return " ".join(tokens)


def _filing_date(raw: str) -> datetime:
    """Parse SUBMISSION.tsv's `FILING_DATE` (`DD-MON-YYYY`, e.g. "31-MAR-2026")
    into a real date.

    Compared as raw strings, these sort by day-of-month first, then month
    NAME alphabetically, then year -- "13-APR-2026" < "13-MAR-2026" (April
    loses to March) and "02-JAN-2027" < "31-DEC-2020" (the year is never
    reached). This archive's amendment dates happened not to cross a
    month-name boundary the wrong way, so a raw-string `max()` produced the
    right winner here by coincidence, not by construction -- confirmed by
    checking all 33 multi-amendment groups against this parsed comparison
    and finding zero mismatches. A December-to-January amendment pair in a
    future period would have picked the wrong one silently.

    Raises rather than falling back to string comparison on a parse
    failure: that would mean the DD-MON-YYYY assumption itself is wrong for
    this archive, which needs to be loud, not quietly patched over.
    """
    try:
        return datetime.strptime(raw, "%d-%b-%Y")
    except ValueError as exc:
        raise ValueError(
            f"FILING_DATE {raw!r} does not match DD-MON-YYYY; refusing to "
            "fall back to string comparison for amendment ordering"
        ) from exc


def resolve_amendments(submissions: dict[str, dict]) -> tuple[dict[str, str], int]:
    """One winning accession per (CIK, PERIODOFREPORT).

    If the group contains any `SUBMISSIONTYPE` ending `/A`, the amendment
    with the latest `FILING_DATE` wins, compared as a parsed date via
    `_filing_date()` (ties broken by accession number, so the choice is
    deterministic even if two amendments file the same day). Every other
    accession in the group — the original(s) it restates, and any earlier
    amendment — is discarded. If the group has no amendment, its (normally
    singular) original wins the same way.

    Returns (accession -> "wins its group" is `accession in returned dict's
    values`, count of groups that required amendment resolution).
    """
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for acc, meta in submissions.items():
        groups[(meta["cik"], meta["period"])].append(acc)

    winner_by_group: dict[tuple[str, str], str] = {}
    amended_groups = 0
    for key, accs in groups.items():
        amends = [a for a in accs if submissions[a]["submission_type"].endswith("/A")]
        pool = amends if amends else accs
        if amends:
            amended_groups += 1
        winner_by_group[key] = max(
            pool, key=lambda a: (_filing_date(submissions[a]["filing_date"]), a))

    return winner_by_group, amended_groups


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--period", default="01mar2026-31may2026")
    args = ap.parse_args()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, legal_name FROM "{PG_SCHEMA_V2}".legal_entity '
                    "WHERE is_anchor ORDER BY legal_name")
        anchors = [(lei, name, _norm_issuer(name)) for lei, name in cur.fetchall()]
    print(f"  matching against {len(anchors)} anchors")

    url = f"{BASE}/{args.period}_form13f.zip"
    if args.dry_run:
        print(f"  [plan] would fetch {url}")
        return 0

    manifest = SourceManifest(
        source="13f",
        description="SEC Form 13F quarterly structured data set — institutional "
                     "holders (SUBMISSION + COVERPAGE + INFOTABLE) filtered to "
                     "anchor issuers",
        licence="US government work / public filing",
    )
    path = fetch(url, manifest, f"{args.period}_form13f.zip", is_sec=True, timeout=300)

    # A quarter's INFOTABLE runs to millions of rows but only on the order of
    # 10-20k distinct NAMEOFISSUER strings. The per-row loop originally called
    # match_score() (50 anchors x every row), which is O(rows x anchors) and
    # measured near two hours of CPU. Memoise on the RAW issuer string instead
    # so each distinct name is resolved once and reused for every row that
    # repeats it. This wraps the *same* match_score() call with the *same*
    # arguments it always had — nothing about the comparison changes, only how
    # many times it runs — so no score or band can shift relative to the
    # un-memoised version. (An earlier draft of this fix tried to shortcut the
    # comparison itself by calling SequenceMatcher directly on the
    # pre-`_norm_issuer` strings, skipping match_score's internal
    # `normalize_name` token-sort. That is NOT equivalent: e.g. "Delta Air
    # Lines" vs "DELTA AIRLINES" scores 0.62 through match_score but 0.97
    # compared directly — a band-flipping difference. Rejected for that
    # reason; match_score itself is reused unmodified, per Tasks 2/4/6.)
    resolved: dict[str, tuple[str, float] | None] = {}

    def resolve_issuer(raw_name: str) -> tuple[str, float] | None:
        """(lei, score) for one NAMEOFISSUER value, or None if nothing bands."""
        if raw_name in resolved:
            return resolved[raw_name]
        issuer = _norm_issuer(raw_name)
        result = None
        if issuer:
            best_lei, best_score = None, 0.0
            for lei, _, normalized in anchors:
                score = match_score(issuer, normalized)
                if score > best_score:
                    best_lei, best_score = lei, score
            if best_score >= WEAK:
                result = (best_lei, best_score)
        resolved[raw_name] = result
        return result

    with zipfile.ZipFile(path) as zf:
        names = {n.upper(): n for n in zf.namelist()}
        cover_name = next(n for u, n in names.items() if u.startswith("COVERPAGE"))
        info_name = next(n for u, n in names.items() if u.startswith("INFOTABLE"))
        submission_name = next(n for u, n in names.items() if u.startswith("SUBMISSION"))

        submissions: dict[str, dict] = {}
        with zf.open(submission_name) as fh:
            for row in csv.DictReader(io.TextIOWrapper(fh, "utf-8", errors="replace"),
                                      delimiter="\t"):
                submissions[row["ACCESSION_NUMBER"]] = {
                    "cik": row["CIK"],
                    "submission_type": row["SUBMISSIONTYPE"],
                    "filing_date": row["FILING_DATE"],
                    "period": row["PERIODOFREPORT"],
                }

        winner_by_group, amended_groups = resolve_amendments(submissions)
        winning_accessions = set(winner_by_group.values())
        print(f"  {len(submissions)} submissions -> {len(winner_by_group)} "
              f"(manager,period) groups, {amended_groups} resolved via amendment")

        manager_names: dict[str, str] = {}
        with zf.open(cover_name) as fh:
            for row in csv.DictReader(io.TextIOWrapper(fh, "utf-8", errors="replace"),
                                      delimiter="\t"):
                manager_names[row["ACCESSION_NUMBER"]] = row.get(
                    "FILINGMANAGER_NAME", "")

        # (lei, manager_cik, cusip, period) -> accumulator. Line items for the
        # same issuer within the ONE winning accession are summed here; rows
        # from a superseded original or a non-latest amendment never reach
        # this loop at all.
        agg: dict[tuple[str, str, str, str], dict] = {}
        skipped_no_submission = 0
        skipped_superseded = 0
        with zf.open(info_name) as fh:
            for row in csv.DictReader(io.TextIOWrapper(fh, "utf-8", errors="replace"),
                                      delimiter="\t"):
                acc = row["ACCESSION_NUMBER"]
                meta = submissions.get(acc)
                if meta is None:
                    skipped_no_submission += 1
                    continue
                if acc not in winning_accessions:
                    skipped_superseded += 1
                    continue

                hit = resolve_issuer(row.get("NAMEOFISSUER", ""))
                if hit is None:
                    continue
                best_lei, best_score = hit

                cusip = row.get("CUSIP", "")
                key = (best_lei, meta["cik"], cusip, meta["period"])
                value = int(row.get("VALUE") or 0)
                shares = int(row.get("SSHPRNAMT") or 0)

                entry = agg.get(key)
                if entry is None:
                    entry = agg[key] = {
                        "lei": best_lei,
                        "manager_cik": meta["cik"],
                        "manager_name": manager_names.get(acc, ""),
                        "cusip": cusip,
                        "value_usd": 0,
                        "shares": 0,
                        "report_period": meta["period"],
                        "issuer_match_score": round(best_score, 4),
                        "issuer_match_band": (
                            "strong" if best_score >= STRONG else "weak"),
                        "provenance": "public",
                    }
                entry["value_usd"] += value
                entry["shares"] += shares

    holders = list(agg.values())

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": f"SEC Form 13F data set {args.period}",
        "holders": holders,
    }
    (SCREEN / "wave10_holders.json").write_text(json.dumps(payload, indent=2))
    strong = sum(1 for h in holders if h["issuer_match_band"] == "strong")
    managers_seen = {h["manager_cik"] for h in holders}
    anchors_seen = {h["lei"] for h in holders}
    print(f"\n  {len(holders)} holdings · {strong} strong / {len(holders) - strong} weak")
    print(f"  {len(managers_seen)} distinct managers · "
          f"{len(anchors_seen)} distinct anchors with >=1 holder")
    print(f"  {len(resolved)} distinct issuer names resolved "
          f"({sum(1 for v in resolved.values() if v is not None)} banded)")
    print(f"  {skipped_no_submission} INFOTABLE rows skipped (accession not in "
          f"SUBMISSION.tsv) · {skipped_superseded} skipped (superseded original "
          "or non-winning amendment)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
