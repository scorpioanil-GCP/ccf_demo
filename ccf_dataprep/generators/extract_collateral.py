#!/usr/bin/env python3
"""Wave 9 — extract collateral, lien, and set-off structure from filed EX-10 text.

`collateral-and-setoff-coverage` §C names **UCC-1 filings** as the strongest
public source for security interests. They are not available to this cast:
under UCC §9-307 a registered organization files in its state of incorporation,
**64% of the anchors are Delaware**, and Delaware's UCC database is not publicly
searchable at all — authorized searchers only, $25/debtor plus a mandatory $25
expedite. Best realistic coverage was ~28% of the cast across five incompatible
state interfaces. Probed and recorded in `docs/data-acquisition-plan.md`.

So this takes the fallback the spec itself sanctions: *"Where UCC data is thin,
the `securedBy` topology falls back to EX-10 collateral schedules, which are
uniformly available but less granular."*

Deterministic-first, same as Wave 4 — credit agreements are conventional in
exactly the places this needs, and every value carries the character offset it
came from so a passage can anchor to it.

**What the fallback cannot supply, and the loader must therefore engineer:**
UCC-1 carries a real *filing date*, and filing date is what establishes priority
between competing secured parties. EX-10 gives contractual first/second-lien
language and no dates. Lien priority is therefore `synthetic — engineered`, not
`public`, and must be labelled that way — presenting an engineered priority
ordering as filed fact would misrepresent the source.

Output: sources/screening/collateral_extracted.json

Run: uv run generators/extract_collateral.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter

from ccf.config import REPO_ROOT, mongo_db, pg_connect, PG_SCHEMA_V2

SCREEN = REPO_ROOT / "sources" / "screening"

#: Asset categories §F asks the ~60 assets to span. Ordered most- to
#: least-specific so `real property` wins over a bare `property` mention.
ASSET_CATEGORIES: list[tuple[str, str]] = [
    ("real_property",
     r"\b(real\s+propert(?:y|ies)|deed\s+of\s+trust|mortgaged\s+propert|"
     r"fee\s+(?:simple\s+)?interest\s+in\s+(?:the\s+)?land)\b"),
    ("marketable_securities",
     r"\b(pledged\s+(?:equity|shares|stock|securities)|investment\s+propert(?:y|ies)|"
     r"marketable\s+securities|capital\s+stock\s+of\s+(?:each|any|its))\b"),
    ("receivables",
     r"\b(accounts?\s+receivable|receivables|accounts\s+(?:and|,)\s+"
     r"(?:chattel\s+paper|general\s+intangibles))\b"),
    ("equipment", r"\bequipment\b"),
    ("inventory", r"\binventory\b"),
    ("deposit_accounts", r"\bdeposit\s+accounts?\b"),
]

#: Structural signals. Presence is what matters; the offset anchors the passage.
STRUCTURE: list[tuple[str, str]] = [
    ("security_agreement", r"\bsecurity\s+agreement\b"),
    ("grants_security_interest",
     r"grants?\s+(?:to\s+[^.]{0,80}?)?a\s+(?:continuing\s+)?security\s+interest"),
    ("pledge_agreement", r"\bpledge\s+agreement\b"),
    ("financing_statement", r"\bfinancing\s+statements?\b"),
    ("negative_pledge", r"\bnegative\s+pledge\b"),
    ("setoff", r"\bset[\s-]?off\b"),
    ("netting", r"\bnetting\b"),
    ("guarantor_schedule",
     r"\b(guarantor\s+schedule|schedule\s+of\s+guarantors|subsidiary\s+guarantors?)\b"),
    ("cross_default", r"\bcross[\s-]?default\b"),
]

#: Lien priority language. NOTE: contractual only — EX-10 carries no filing date,
#: so this establishes *relative* seniority, never a filed priority position.
PRIORITY: list[tuple[str, str]] = [
    ("first_lien", r"\bfirst[\s-]?(?:priority\s+)?lien\b"),
    ("second_lien", r"\bsecond[\s-]?(?:priority\s+)?lien\b"),
    ("senior_secured", r"\bsenior\s+secured\b"),
    ("subordinated_lien", r"\b(junior|subordinated)[\s-]?lien\b"),
]


def first_match(text: str, pattern: str) -> tuple[int, str] | None:
    """(offset, matched_text) of the first hit, or None."""
    m = re.search(pattern, text, re.I)
    return (m.start(), m.group(0)[:80]) if m else None


def all_offsets(text: str, pattern: str, cap: int = 25) -> list[int]:
    return [m.start() for m in re.finditer(pattern, text, re.I)][:cap]


#: A granting clause is where collateral is actually pledged. Category words
#: appearing anywhere else are boilerplate — definitions, representations,
#: negative covenants describing what the borrower may NOT do.
GRANT_ANCHOR = (r"grants?\s+(?:to\s+[^.]{0,80}?)?a\s+(?:continuing\s+)?security\s+"
                r"interest|\bCollateral\s+(?:shall\s+mean|means)|"
                r"\bpledges?,?\s+(?:and\s+)?(?:assigns|grants|hypothecates)")

#: Characters either side of a granting clause still plausibly inside it.
GRANT_WINDOW = 2500


def extract(text: str) -> dict:
    """Everything Wave 9 needs from one filed document, with offsets."""
    out: dict = {"asset_categories": {}, "structure": {}, "priority": {}}

    # Windows around every granting clause. A category is treated as PLEDGED
    # only inside one of these; elsewhere it is merely mentioned.
    grant_spans = [(max(0, m.start() - GRANT_WINDOW), m.end() + GRANT_WINDOW)
                   for m in re.finditer(GRANT_ANCHOR, text, re.I)]

    def in_grant(offset: int) -> bool:
        return any(lo <= offset <= hi for lo, hi in grant_spans)

    for name, pat in ASSET_CATEGORIES:
        offs = all_offsets(text, pat)
        if not offs:
            continue
        pledged = [o for o in offs if in_grant(o)]
        hit = first_match(text, pat)
        out["asset_categories"][name] = {
            "mentions": len(offs),
            "pledged_mentions": len(pledged),
            # The distinction that keeps this honest: mentioned != pledged.
            "pledged": bool(pledged),
            "first_offset": pledged[0] if pledged else offs[0],
            "excerpt": hit[1] if hit else "",
        }
    out["grant_clauses"] = len(grant_spans)
    for name, pat in STRUCTURE:
        hit = first_match(text, pat)
        if hit:
            out["structure"][name] = {"offset": hit[0], "excerpt": hit[1]}
    for name, pat in PRIORITY:
        hit = first_match(text, pat)
        if hit:
            out["priority"][name] = {"offset": hit[0], "excerpt": hit[1]}

    # Secured at all? `grants a security interest` is the operative language;
    # a bare "collateral" mention can be a defined term with no grant behind it.
    out["is_secured"] = bool(
        out["structure"].get("grants_security_interest")
        or out["structure"].get("security_agreement")
    )
    return out


def main() -> int:
    db = mongo_db()
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT facility_id, borrower_lei, facility_type, commitment_amount,
                   currency, source_document, source_accession
            FROM "{PG_SCHEMA_V2}".facility ORDER BY facility_id
        """)
        facilities = [
            {"facility_id": r[0], "borrower_lei": r[1], "facility_type": r[2],
             "commitment_amount": float(r[3]) if r[3] is not None else None,
             "currency": r[4], "source_document": r[5], "source_accession": r[6]}
            for r in cur.fetchall()
        ]

    print(f"Wave 9 — collateral extraction over {len(facilities)} facilities\n")
    print("  UCC-1 unavailable for this cast (64% Delaware, closed to public")
    print("  search). Falling back to EX-10 per spec §C.\n")

    # One document may back several facilities; parse each document once.
    cache: dict[str, dict] = {}
    results, unresolved = [], 0
    for f in facilities:
        key = f["source_document"]
        if key not in cache:
            doc = db["document"].find_one(
                {"document_id": key}, {"text": 1, "sec_name": 1}
            ) or db["document"].find_one(
                {"accession": f["source_accession"]}, {"text": 1, "sec_name": 1}
            )
            cache[key] = extract(doc["text"]) if doc and doc.get("text") else {}
        ext = cache[key]
        if not ext:
            unresolved += 1
            continue
        results.append({**f, **ext})

    secured = [r for r in results if r["is_secured"]]
    cat_counts = Counter(c for r in results for c in r["asset_categories"])
    pledged_counts = Counter(
        c for r in results for c, v in r["asset_categories"].items() if v["pledged"]
    )
    struct_counts = Counter(s for r in results for s in r["structure"])
    prio_counts = Counter(p for r in results for p in r["priority"])

    print(f"  resolved to a document      {len(results)}/{len(facilities)}"
          + (f"  ({unresolved} unresolved)" if unresolved else ""))
    print(f"  facilities showing a grant  {len(secured)}\n")

    print("  ASSET CATEGORIES        mentioned / PLEDGED-in-granting-clause")
    print("  (a credit agreement mentions everything; only the second column")
    print("   means the asset was actually granted as collateral)")
    for name, _ in ASSET_CATEGORIES:
        print(f"    {name:<24} {cat_counts.get(name, 0):>3}  /"
              f"{pledged_counts.get(name, 0):>4}")
    print("\n  STRUCTURE")
    for name, _ in STRUCTURE:
        print(f"    {name:<24} {struct_counts.get(name, 0):>3}")
    print("\n  LIEN PRIORITY  (contractual language only — no filing dates)")
    for name, _ in PRIORITY:
        print(f"    {name:<24} {prio_counts.get(name, 0):>3}")

    out = SCREEN / "collateral_extracted.json"
    out.write_text(json.dumps({
        "wave": 9,
        "source": "EDGAR EX-10 exhibits already cached in MongoDB fibo_v2",
        "ucc_status": ("unavailable — 64% of the cast files in Delaware, whose "
                       "UCC database is not publicly searchable; see "
                       "docs/data-acquisition-plan.md Wave 9 decision"),
        "priority_provenance": ("synthetic — engineered. EX-10 gives contractual "
                                "seniority language but no filing dates, and "
                                "filing date is what establishes UCC priority."),
        "facilities": results,
    }, indent=2) + "\n")
    print(f"\n  written: {out.relative_to(REPO_ROOT)}")

    # §F floors this extraction is responsible for feeding.
    print("\n  §F readiness")
    checks = [
        ("~40 facilities", len(results), 40),
        ("4 asset categories actually PLEDGED",
         sum(1 for c in ("real_property", "marketable_securities",
                         "receivables", "equipment") if pledged_counts.get(c)), 4),
        ("≥1 negative pledge", struct_counts.get("negative_pledge", 0), 1),
        ("priority language for shared-collateral cases",
         prio_counts.get("first_lien", 0) + prio_counts.get("second_lien", 0), 2),
        ("set-off language", struct_counts.get("setoff", 0), 1),
    ]
    for label, actual, floor in checks:
        print(f"    [{'ok  ' if actual >= floor else 'FAIL'}] {label:<44} "
              f"{actual} / {floor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
