#!/usr/bin/env python3
"""Wave 1 — resolve anchor obligors to real GLEIF LEIs.

Settled decision (CLAUDE.md): public anchor obligors carry **real GLEIF LEIs**,
because several specs join public sources on LEI -> CIK -> ticker and fake
identifiers cannot join. Invented entities carry synthetic identifiers in a
visibly distinct format so the two can never be confused.

This resolves each anchor's SEC-registered name against the GLEIF API and
records the match with a confidence band, so a weak match is visible rather
than silently accepted.

Note on deliberate imperfection: non-negotiable rule #5 requires some joins to
be imperfect *on purpose* — but that belongs to person-name resolution in
kyc-refresh-beneficial-ownership, not here. The anchor spine must be correct;
ambiguity here would corrupt every downstream product.

Output: sources/screening/lei_matches.json

Run: uv run generators/resolve_leis.py
"""

from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher

import requests

from ccf.config import REPO_ROOT
from ccf.fetch import DEFAULT_LIMITER

GLEIF_SEARCH = "https://api.gleif.org/api/v1/lei-records"
IN_PATH = REPO_ROOT / "sources" / "screening" / "anchors.json"
OUT_PATH = REPO_ROOT / "sources" / "screening" / "lei_matches.json"

#: Note `incorporated` must appear alongside `inc`. Omitting it made
#: "GRANITE CONSTRUCTION INC" vs "GRANITE CONSTRUCTION INCORPORATED" score
#: 0.755 and get rejected as a mismatch, when it is the same company.
SUFFIXES = re.compile(
    r"\b(incorporated|inc|corporation|corp|company|co|limited|ltd|llc|lp|plc|"
    r"holdings?|group|the|sa|nv|ag|international|intl)\b\.?",
    re.IGNORECASE,
)
PUNCT = re.compile(r"[^a-z0-9 ]+")


def normalize(name: str) -> str:
    name = name.lower()
    name = re.sub(r"/[a-z]{2}/?$", "", name)      # EDGAR state suffix e.g. /MO/
    name = PUNCT.sub(" ", name)
    name = SUFFIXES.sub(" ", name)
    return " ".join(name.split())


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def band(score: float) -> str:
    if score >= 0.95:
        return "exact"
    if score >= 0.85:
        return "strong"
    if score >= 0.70:
        return "weak"
    return "poor"


def search_gleif(name: str, *, size: int = 5) -> list[dict]:
    DEFAULT_LIMITER.wait()
    try:
        resp = requests.get(
            GLEIF_SEARCH,
            params={"filter[entity.legalName]": name, "page[size]": size},
            timeout=25,
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("data", [])
    except Exception:  # noqa: BLE001
        return []


def fuzzy_gleif(name: str, *, size: int = 8) -> list[dict]:
    """GLEIF fulltext fallback when the exact legalName filter misses."""
    DEFAULT_LIMITER.wait()
    try:
        resp = requests.get(
            GLEIF_SEARCH,
            params={"filter[fulltext]": name, "page[size]": size},
            timeout=25,
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("data", [])
    except Exception:  # noqa: BLE001
        return []


#: EDGAR abbreviates where GLEIF spells out. Without expansion the exact
#: legalName filter misses and the fulltext fallback returns unrelated
#: entities — "WD 40 CO" matched PUDO INVESTMENTS LIMITED on a first pass.
EXPANSIONS = [
    (re.compile(r"\bCORP\b\.?", re.I), "CORPORATION"),
    (re.compile(r"\bCO\b\.?(?!RP)", re.I), "COMPANY"),
    (re.compile(r"\bINC\b\.?", re.I), "INCORPORATED"),
    (re.compile(r"\bLTD\b\.?", re.I), "LIMITED"),
    (re.compile(r"\bINTL\b\.?", re.I), "INTERNATIONAL"),
    (re.compile(r"\bHLDGS\b\.?", re.I), "HOLDINGS"),
    (re.compile(r"\bTECH\b\.?", re.I), "TECHNOLOGIES"),
]

EDGAR_SUFFIX = re.compile(r"\s*/[A-Z]{2}/?\s*$")


def name_variants(sec_name: str) -> list[str]:
    """Query forms to try against GLEIF, most literal first."""
    base = EDGAR_SUFFIX.sub("", sec_name).strip()
    variants = [base]

    expanded = base
    for pattern, replacement in EXPANSIONS:
        expanded = pattern.sub(replacement, expanded)
    if expanded != base:
        variants.append(expanded)

    # "WD 40" -> "WD-40": EDGAR drops hyphens GLEIF keeps.
    hyphenated = re.sub(r"\b([A-Z]{2,})\s+(\d+)\b", r"\1-\2", expanded)
    if hyphenated not in variants:
        variants.append(hyphenated)

    # Drop a trailing corporate suffix entirely — GLEIF sometimes registers
    # the bare trading name.
    bare = SUFFIXES.sub("", base).strip(" ,.")
    if bare and bare not in variants:
        variants.append(bare)

    return variants


def best_match(sec_name: str) -> dict | None:
    candidates: list[dict] = []
    seen_leis: set[str] = set()

    for variant in name_variants(sec_name):
        for rec in search_gleif(variant):
            lei = rec.get("attributes", {}).get("lei", "")
            if lei and lei not in seen_leis:
                seen_leis.add(lei)
                candidates.append(rec)
        # Stop early on a confident hit rather than burning API calls.
        if any(
            similarity(
                sec_name,
                (r.get("attributes", {}).get("entity", {}).get("legalName") or {}).get("name", ""),
            )
            >= 0.95
            for r in candidates
        ):
            break

    if not candidates:
        stem = normalize(sec_name)
        if stem:
            candidates = fuzzy_gleif(stem)
    if not candidates:
        return None

    scored = []
    for rec in candidates:
        attrs = rec.get("attributes", {})
        entity = attrs.get("entity", {})
        legal_name = (entity.get("legalName") or {}).get("name", "")
        if not legal_name:
            continue
        scored.append((similarity(sec_name, legal_name), rec, legal_name))
    if not scored:
        return None

    scored.sort(key=lambda t: t[0], reverse=True)
    score, rec, legal_name = scored[0]
    attrs = rec.get("attributes", {})
    entity = attrs.get("entity", {})
    registration = attrs.get("registration", {})
    legal_addr = entity.get("legalAddress", {}) or {}

    return {
        "lei": attrs.get("lei", ""),
        "gleif_legal_name": legal_name,
        "match_score": round(score, 3),
        "match_band": band(score),
        "entity_status": entity.get("status", ""),
        "registration_status": registration.get("status", ""),
        "next_renewal_date": registration.get("nextRenewalDate", ""),
        "initial_registration_date": registration.get("initialRegistrationDate", ""),
        "legal_form": (entity.get("legalForm") or {}).get("id", ""),
        "legal_jurisdiction": entity.get("jurisdiction", ""),
        "legal_address_country": legal_addr.get("country", ""),
        "legal_address_city": legal_addr.get("city", ""),
        "legal_address_region": legal_addr.get("region", ""),
        "alternatives": [
            {"lei": r.get("attributes", {}).get("lei", ""), "name": n,
             "score": round(s, 3)}
            for s, r, n in scored[1:3]
        ],
    }


def main() -> int:
    if not IN_PATH.exists():
        print(f"missing {IN_PATH} — run generators/select_anchors.py first")
        return 1

    anchors = json.loads(IN_PATH.read_text())["anchors"]
    print(f"Resolving {len(anchors)} anchors against GLEIF\n")

    results = []
    for i, anchor in enumerate(anchors, 1):
        match = best_match(anchor["name"])
        row = {
            "cik": anchor["cik"],
            "sec_name": anchor["name"],
            "tickers": anchor["tickers"],
            "sic": anchor["sic"],
            "seated_for": anchor["seated_for"],
        }
        # Reject rather than accept a wrong LEI. A bad anchor match corrupts
        # every downstream join, and a silently wrong spine is exactly the
        # failure mode CLAUDE.md warns is expensive to discover later.
        if match and match["match_band"] in ("exact", "strong"):
            row.update(match)
            row["accepted"] = True
        elif match:
            row.update(match)
            row["accepted"] = False
            row["rejection_reason"] = (
                f"match band '{match['match_band']}' below threshold 'strong'"
            )
        else:
            row.update({"lei": "", "match_band": "none", "match_score": 0.0,
                        "accepted": False,
                        "rejection_reason": "no GLEIF candidate returned"})
        results.append(row)
        if i % 10 == 0:
            print(f"  ...{i}/{len(anchors)}")

    bands: dict[str, int] = {}
    for r in results:
        bands[r["match_band"]] = bands.get(r["match_band"], 0) + 1

    resolved = [r for r in results if r.get("accepted")]
    lapsed = [r for r in resolved
              if r.get("registration_status") not in ("ISSUED", "")]

    OUT_PATH.write_text(
        json.dumps(
            {
                "generated_for": "Wave 1 — GLEIF LEI resolution for anchor cast",
                "source": "https://api.gleif.org/api/v1/lei-records",
                "total": len(results),
                "resolved": len(resolved),
                "bands": bands,
                "matches": results,
            },
            indent=2,
        )
        + "\n"
    )

    print(f"\n  written: {OUT_PATH.relative_to(REPO_ROOT)}\n")
    print(f"  resolved {len(resolved)}/{len(results)} to a real LEI")
    for b in ("exact", "strong", "weak", "poor", "none"):
        if b in bands:
            print(f"    {b:8s} {bands[b]:>3}")

    print(f"\n  registration status (feeds the ~5 LAPSED requirement):")
    status: dict[str, int] = {}
    for r in resolved:
        s = r.get("registration_status", "?")
        status[s] = status.get(s, 0) + 1
    for s, n in sorted(status.items(), key=lambda kv: -kv[1]):
        print(f"    {s:16s} {n:>3}")

    rejected = [r for r in results if not r.get("accepted")]
    if rejected:
        print(f"\n  {len(rejected)} REJECTED — not loaded, would corrupt the spine:")
        for r in rejected:
            print(f"    {r['sec_name'][:32]:34s} -> "
                  f"{r.get('gleif_legal_name', '(none)')[:28]:30s} "
                  f"{r['match_score']}  [{r['match_band']}]")
    else:
        print("\n  no rejections — every anchor resolved at 'strong' or better")

    return 0


if __name__ == "__main__":
    sys.exit(main())
