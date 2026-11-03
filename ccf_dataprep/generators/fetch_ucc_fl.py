#!/usr/bin/env python3
"""Fetch Florida UCC-1 filings for a debtor name list.

`collateral-and-setoff-coverage` §C names three elements sourced from UCC-1
filings, and the vault's own note of 2026-08-24 records that the filing-date
half has never been loaded:

    | Lien filing date | UCC-1 filing records -- **not loaded** | public | Fluree | R, T |

Wave 9 (2026-08-17) ruled UCC-1 non-viable for this cast because 64% of the
anchors are Delaware-domiciled and Delaware's register is closed to public
search. That holds for Delaware. What it missed is that a financing statement
is filed against the **debtor**, and a Delaware parent's operating subsidiaries
incorporate elsewhere -- so the cast's reach is its subsidiaries' domiciles,
not its parents'.

Florida publishes an unauthenticated JSON API over its Secured Transaction
Registry. This fetches from it.

## searchCategory is the trap in this API

`Standard` is a **proximity browse**: it returns the twenty alphabetically
nearest debtor names whether or not any of them matches the query. Every call
appears to succeed, with exactly twenty results, for any input. Measured across
a 20-name sample it reported a 100% hit rate; `Exact` reported 45%.

Only `Exact` filters, and only `Exact` populates `totalExactMatches`. This
module therefore uses `Exact` exclusively, and `probe_discriminates()` asserts
at run time that a known-present name returns a non-zero count while a
known-absent one returns zero. A search client that cannot return zero is not
searching, and would quietly populate the estate with whatever happened to be
alphabetically nearby.

## What this does not fetch

The collateral description. It exists only inside a scanned `.tif` reachable
via `/filing-image`, which returns a **signed, expiring** CloudFront URL. OCR
of scanned forms is error-prone, and a mis-read collateral description stored
as filed fact is worse than an honest absence -- so collateral description
stays EX-10-derived, as it is today, and no image URL is persisted.

Run: uv run --with pytest generators/fetch_ucc_fl.py --names MASTEC
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ccf import fetch as ccf_fetch  # noqa: E402

API = "https://publicsearchapi.floridaucc.com"
SOURCE = "ucc_fl"

#: The registry's organisation-debtor index. `Exact` is mandatory -- see the
#: module docstring.
SEARCH_OPTION_TYPE = "OrganizationDebtorName"
SEARCH_OPTION_SUB = "FiledCompactDebtorNameList"
SEARCH_CATEGORY = "Exact"

#: Controls for `probe_discriminates`. The present name is a real Florida
#: debtor verified 2026-09-10; the absent one is nonsense by construction.
CONTROL_PRESENT = "MASTEC, INC."
CONTROL_ABSENT = "ZZQQXX NOT A REAL COMPANY LLC"


def _manifest() -> ccf_fetch.SourceManifest:
    return ccf_fetch.SourceManifest(
        source=SOURCE,
        description=(
            "Florida Secured Transaction Registry -- UCC-1 financing statements "
            "and UCC-3 amendments, organisation-debtor index. Unauthenticated "
            "public JSON API."
        ),
        licence="Florida public record. Non-certified search results.",
    ).load()


def _url(path: str, **params: Any) -> str:
    from urllib.parse import urlencode
    return f"{API}{path}?{urlencode(params)}"


def search(name: str) -> dict:
    """Exact-match debtor search. Returns the raw payload."""
    return ccf_fetch.get_json(_url(
        "/search",
        text=name,
        searchOptionType=SEARCH_OPTION_TYPE,
        searchOptionSubOption=SEARCH_OPTION_SUB,
        searchCategory=SEARCH_CATEGORY,
        pageNumber=1,
    ))["payload"]


def filing_details(row_number: int, name: str) -> dict:
    return ccf_fetch.get_json(_url(
        "/filing-details",
        rowNumber=row_number,
        searchOptionSubOption=SEARCH_OPTION_SUB,
        searchCategory=SEARCH_CATEGORY,
        text=name,
    ))["payload"]


def filing_history(ucc1_number: str) -> list[dict]:
    """Amendment (UCC-3) history for a UCC-1.

    The registry answers **404 for a filing that has no amendments** rather
    than returning an empty list. That is a legitimate "none", so it is
    translated to `[]` here -- but only for 404, and never for any other
    status. `collect()` then cross-checks the result against the detail
    payload's own `filingEvents` count, so a 404 that should have been a
    populated history is caught rather than silently becoming "no amendments".
    Swallowing the 404 without that oracle would make every filing look
    unamended, which is exactly the direction this product must not fail in --
    an amendment is what changes whether a lien is still live.
    """
    import requests
    try:
        payload = ccf_fetch.get_json(_url(
            "/filing-history",
            ucc1Number=ucc1_number,
            pageSize=50,
            currentPage=1,
            sortOrder="Descending",
            orderColumnName="FilingDate",
        ))
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            return []
        raise
    return payload.get("payload") or []


def completed_through() -> str:
    """The registry's statement of its own currency -- the as-of for a pull."""
    return ccf_fetch.get_json(f"{API}/filings-completed-through-date")["payload"]


def probe_discriminates() -> None:
    """Fail loudly unless the search can return BOTH a hit and a zero.

    This is the positive/negative control pair. It exists because the same
    endpoint, called with `searchCategory=Standard`, returns twenty results
    for literally any input -- including names that do not exist. A pull built
    on that mode would look complete and be meaningless.
    """
    present = search(CONTROL_PRESENT).get("totalExactMatches") or 0
    absent = search(CONTROL_ABSENT).get("totalExactMatches") or 0
    if present <= 0:
        raise RuntimeError(
            f"positive control failed: {CONTROL_PRESENT!r} returned "
            f"{present} exact matches. The search is not finding a name known "
            f"to be present, so a zero for any other name proves nothing."
        )
    if absent != 0:
        raise RuntimeError(
            f"negative control failed: {CONTROL_ABSENT!r} returned {absent} "
            f"exact matches. The search cannot return zero, so every result "
            f"is suspect -- check that searchCategory is {SEARCH_CATEGORY!r} "
            f"and not 'Standard'."
        )
    print(f"  controls ok: {CONTROL_PRESENT!r}={present}, "
          f"{CONTROL_ABSENT!r}={absent}")


def collect(names: list[str]) -> dict:
    """Search each name, then pull details and amendment history for each hit."""
    probe_discriminates()
    as_of = completed_through()
    print(f"  registry complete through {as_of}")

    out: dict[str, Any] = {
        "source": "Florida Secured Transaction Registry",
        "api": API,
        "filings_completed_through": as_of,
        "search_category": SEARCH_CATEGORY,
        "provenance": "public",
        "names_searched": len(names),
        "debtors": [],
    }

    for name in names:
        # One unsearchable name must not end the run -- but it must not
        # vanish either. Failures are recorded by name and reported, so a
        # pull that searched 63 names and could only search 61 says so.
        # Silent per-name failure is how a coverage claim quietly becomes
        # a claim about a smaller population than it names.
        try:
            payload = search(name)
        except Exception as exc:  # noqa: BLE001 -- recorded, not swallowed
            status = getattr(getattr(exc, "response", None), "status_code", None)
            out.setdefault("search_failures", []).append({
                "name": name,
                "error": type(exc).__name__,
                "http_status": status,
                "length": len(name),
            })
            print(f"  FAIL   {name[:60]!r} ({type(exc).__name__} {status})")
            continue
        n = payload.get("totalExactMatches") or 0
        debtors = payload.get("debtors") or []
        print(f"  {n:4} exact  {name}")
        if not debtors:
            continue
        for d in debtors:
            detail = filing_details(d["rowNumber"], name)
            if not detail:
                continue
            ucc1 = detail.get("ucc1Number") or detail.get("uccNumber")
            events = detail.get("filingEvents") or 0
            amendments = filing_history(ucc1) if ucc1 else []

            # The detail payload counts filing events; the history endpoint
            # lists them. A UCC-1 with no amendments reports filingEvents=1
            # (itself) and 404s on history. If the count says there are
            # amendments and the list is empty, the 404-to-[] translation
            # above has hidden something -- say so rather than record a lien
            # as unamended when the registry says it was touched.
            if events > 1 and not amendments:
                out.setdefault("inconsistencies", []).append({
                    "ucc1_number": ucc1,
                    "filing_events": events,
                    "amendments_returned": 0,
                    "note": "detail reports amendments; history returned none",
                })

            record = {
                "searched_name": name,
                "filed_debtor_name": d.get("name"),
                "ucc_number": detail.get("uccNumber"),
                "ucc1_number": ucc1,
                "file_date": detail.get("fileDate"),
                "expiration_date": detail.get("expirationDate"),
                "status": detail.get("status"),
                "document_type": detail.get("documentType"),
                "debtors": detail.get("debtors") or [],
                "secured_parties": detail.get("secureds") or [],
                "filing_events": events,
                "amendments": amendments,
            }
            out["debtors"].append(record)

    out["filings_retrieved"] = len(out["debtors"])
    out["names_searched_ok"] = len(names) - len(out.get("search_failures", []))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--names", nargs="+",
                     help="debtor names to search, verbatim as filed")
    src.add_argument("--names-file",
                     help="file of debtor names, one per line")
    ap.add_argument("--out", default="mastec.json",
                    help="filename under sources/ucc_fl/")
    args = ap.parse_args()

    if args.names_file:
        names = [ln.strip() for ln in Path(args.names_file).read_text().splitlines()
                 if ln.strip()]
    else:
        names = args.names

    man = _manifest()
    man.directory.mkdir(parents=True, exist_ok=True)

    data = collect(names)
    target = man.directory / args.out
    payload = json.dumps(data, indent=2) + "\n"
    target.write_text(payload)
    _record_pull(man, target, payload, data)

    print(f"\n  {data['filings_retrieved']} filings -> {target}")
    print(f"  as-of {data['filings_completed_through']}")
    print(f"  provenance recorded in {man.manifest_path}")
    return 0


def _record_pull(man: ccf_fetch.SourceManifest, target: Path,
                 payload: str, data: dict) -> None:
    """Record this pull in the source manifest.

    `ccf.fetch.fetch()` records one URL per payload, which is the right shape
    when one URL yields one file. This pull composes **hundreds** of calls
    across three endpoints into a single artifact, so there is no single URL
    to record and 200 near-identical entries would bury the fact that matters.

    One record is written instead, keyed on the search endpoint, carrying the
    sha256 and byte count of the composed artifact plus -- in `notes` -- the
    registry's own `filings-completed-through` stamp, the search mode, and how
    many names were searched versus how many could be. Those are the facts a
    reader needs to know what this snapshot is and what it is missing.
    """
    import hashlib
    from datetime import datetime, timezone

    raw = payload.encode()
    failures = len(data.get("search_failures", []))
    man.fetches = [f for f in man.fetches if f.path != ccf_fetch._record_path(target)]
    man.fetches.append(ccf_fetch.FetchRecord(
        url=f"{API}/search",
        path=ccf_fetch._record_path(target),
        retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        sha256=hashlib.sha256(raw).hexdigest(),
        bytes=len(raw),
        http_status=200,
        content_type="application/json",
        notes=(
            f"composed pull: {data['names_searched']} names searched, "
            f"{data['names_searched_ok']} succeeded, {failures} failed; "
            f"{data['filings_retrieved']} filings; "
            f"searchCategory={data['search_category']}; "
            f"registry complete through {data['filings_completed_through']}"
        ),
    ))
    man.save()


if __name__ == "__main__":
    raise SystemExit(main())
