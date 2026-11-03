#!/usr/bin/env python3
"""Wave 13a stage 3 — 10-K Item 1A/7, 10-Q MD&A and 8-K EX-99 for the memo set.

    uv run generators/fetch_narrative_docs.py --dry-run
    uv run generators/fetch_narrative_docs.py

`credit-memo-context` §C names three document elements this estate holds none
of. MongoDB currently carries 59 documents and every one is an EX-10 credit
agreement inherited from `covenant-cross-reference`, so the narrative text the
memo is actually written from has **zero** representation.

**Items, not whole filings.** §C asks for *"10-K Item 1A risk factors, Item 7
MD&A"* and *"10-Q MD&A"* -- named sections, not the documents containing them.
A 10-K runs to several megabytes and is mostly financial statements and
exhibits that this product never cites. Extracting the named items keeps the
corpus proportionate to what a memo cites and faithful to the catalog.

**The table-of-contents trap, handled explicitly.** Every 10-K opens with a
contents table listing "Item 1A. Risk Factors" and "Item 7. Management's
Discussion and Analysis" as links. A first-match extractor therefore returns
the table-of-contents ROW -- a few dozen characters -- and reports success. The
resulting passage is a heading with no content, and nothing downstream can tell
it apart from a section that genuinely says little.

So candidate headings are scored by **how much text follows before the next
item boundary**, and the largest span wins. A TOC entry is followed immediately
by the next TOC entry, so it scores near zero and loses. `MIN_SECTION_CHARS`
then rejects anything still implausibly short rather than storing it, because a
120-character "Item 1A" is not a risk-factors section and should be visible as
a gap rather than counted as coverage.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import REPO_ROOT, pg_connect
from ccf.fetch import SourceManifest, fetch, get_json
from ccf.memo_grade import memo_grade_leis
from generators.extract_facilities import TextExtractor

SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave13a_narrative_index.json"

SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
FILING_INDEX = "https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/index.json"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/{doc}"

#: A section shorter than this is a table-of-contents artefact or a
#: cross-reference stub, not the section itself. Recorded as a gap, never
#: stored as coverage.
MIN_SECTION_CHARS = 1500

#: How many recent 8-Ks to consider when looking for an EX-99 exhibit.
EIGHTK_LOOKBACK = 12

#: Typographic characters EDGAR filings use in headings, mapped to their ASCII
#: equivalents so one pattern matches both. Observed live: BGC's 10-K reads
#: "Item 7, Management’s Discussion" -- a RIGHT SINGLE QUOTATION MARK and a
#: comma, neither of which the first version of these patterns matched, so
#: every Item 7 in the probe reported "section heading not found".
#:
#: **Every entry MUST be 1:1 in character count.** Offsets are the join in this
#: estate -- a passage anchor is {document_id, start_offset, end_offset} and
#: Wave 6 verifies it by hashing the span. A substitution that changed length
#: would shift every subsequent offset while still hashing cleanly against the
#: altered text, which is an anchor that verifies and points at the wrong
#: words. Asserted in `check_normalise_is_length_preserving`.
NORMALISE = str.maketrans({
    "’": "'", "‘": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ",
})

#: Separator between an item number and its title. Filings use a period, a
#: comma, a colon, a dash, or nothing at all.
SEP = r"\s*[.,:;\-]?\s*"

#: (label, start pattern, end patterns). Ends are the items that conventionally
#: follow, so the span stops where the next item begins.
SECTIONS = {
    "10-K": [
        ("risk_factors", rf"item\s*1a{SEP}risk\s+factors",
         [rf"item\s*1b{SEP}", rf"item\s*2{SEP}propert"]),
        ("mdna", rf"item\s*7{SEP}management'?s?\s+discussion",
         [rf"item\s*7a{SEP}", rf"item\s*8{SEP}financial\s+statements"]),
    ],
    "10-Q": [
        ("mdna", rf"item\s*2{SEP}management'?s?\s+discussion",
         [rf"item\s*3{SEP}quantitative", rf"item\s*4{SEP}controls"]),
    ],
}


def best_span(text: str, start_pat: str,
              end_pats: list[str]) -> tuple[int, int, bool] | None:
    """Return (start, end, bounded) for the best candidate heading.

    Two rules, and the second exists because the first alone is wrong.

    **Never first-match.** A 10-K's table of contents repeats every item
    heading, so the first "Item 1A" is a TOC row followed immediately by the
    next TOC row. Candidates are therefore ranked by how much text follows.

    **Prefer a candidate whose END boundary was actually found.** The first
    version of this ranked purely on span length and fell back to
    `end = len(text)` when no following item matched -- which made a MISSED end
    boundary the largest span and therefore the winner. It produced a 590,667
    character "Item 1A" for BGC and a 441,683 character "Item 7" for CION:
    the named section plus the entire rest of the filing, silently, scoring
    best precisely because it was wrong. Bounded candidates now win outright;
    an unbounded one is returned only if nothing is bounded, and is flagged so
    the caller can refuse it.
    """
    starts = [m.start() for m in re.finditer(start_pat, text, re.I)]
    if not starts:
        return None
    cands: list[tuple[int, int, bool]] = []
    for st in starts:
        end, bounded = len(text), False
        for ep in end_pats:
            m = re.search(ep, text[st + 50:], re.I)
            if m:
                cand_end = st + 50 + m.start()
                if cand_end < end:
                    end, bounded = cand_end, True
        cands.append((st, end, bounded))
    bounded_only = [c for c in cands if c[2]]
    pool = bounded_only or cands
    return max(pool, key=lambda c: c[1] - c[0])


def latest_filings(cik: int) -> tuple[dict[str, tuple[str, str, str]],
                                      list[tuple[str, str, str]]]:
    """Most recent 10-K, 10-Q and 8-K as (accession, filed_date, primary_doc).

    `primaryDocument` comes from the submissions index and is authoritative.
    An earlier version picked the first `.htm` in the filing directory instead
    and got `*-index-headers.html` every time -- EDGAR's own metadata wrapper,
    which parses cleanly, contains no item headings, and therefore produced a
    confident "section heading not found" for every 10-K and 10-Q.

    `recent`-only, so a FLOOR on the issuer's history — the estate-wide caveat
    in known-issues.md §9.11. Harmless here: this product wants the LATEST
    narrative, which is what `recent` is guaranteed to hold.
    """
    try:
        sub = get_json(SUBMISSIONS.format(cik=cik), is_sec=True, timeout=60)
    except Exception:  # noqa: BLE001
        return {}, []
    rec = sub.get("filings", {}).get("recent", {})
    forms, accns = rec.get("form", []), rec.get("accessionNumber", [])
    dates, prim = rec.get("filingDate", []), rec.get("primaryDocument", [])
    out: dict[str, tuple[str, str, str]] = {}
    eights: list[tuple[str, str, str]] = []
    for i, form in enumerate(forms):
        row = (accns[i],
               dates[i] if i < len(dates) else "",
               prim[i] if i < len(prim) else "")
        if form == "8-K":
            # Not every 8-K carries an EX-99 -- most announce something with no
            # exhibit at all. Taking only the most recent one made "no EX-99"
            # the commonest gap in the probe, which measured our sampling
            # rather than the filer. Collect candidates; the caller walks them.
            if len(eights) < EIGHTK_LOOKBACK:
                eights.append(row)
        elif form in ("10-K", "10-Q") and form not in out:
            out[form] = row
    if eights:
        out["8-K"] = eights[0]
    return out, eights


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="cap obligors, for probing")
    args = ap.parse_args()

    leis = sorted(memo_grade_leis())
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, legal_name FROM "{S}".legal_entity '
                    "WHERE lei = ANY(%s)", (leis,))
        names = dict(cur.fetchall())
    anchors = json.loads((SCREEN / "anchors_final.json").read_text())["anchors"]
    cik_of = {a["lei"]: a["cik"] for a in anchors if a.get("lei")}

    targets = [l for l in leis if l in cik_of]
    if args.limit:
        targets = targets[:args.limit]
    print("Wave 13a — narrative documents for the memo-grade set\n")
    print(f"  {len(targets)} obligors with a CIK "
          f"(of {len(leis)} memo-grade)\n")

    manifest = SourceManifest(
        source="narrative",
        description="EDGAR 10-K Item 1A/7, 10-Q Item 2 MD&A and 8-K EX-99 "
                    "sections for the memo-grade obligor set",
        licence="US government work / public filing",
    ).load()
    records, gaps = [], []

    for lei in targets:
        cik = cik_of[lei]
        filings, eights = latest_filings(cik)
        for form, (accn, filed, primary) in filings.items():
            nodash = accn.replace("-", "")
            if form == "8-K":
                # EX-99 is an exhibit, so it is never `primaryDocument`; the
                # filing directory is the only place to find it. Walk recent
                # 8-Ks until one actually carries one.
                doc = None
                for cand_accn, cand_filed, _ in eights:
                    cand_nodash = cand_accn.replace("-", "")
                    try:
                        idx = get_json(
                            FILING_INDEX.format(cik=cik, nodash=cand_nodash),
                            is_sec=True, timeout=60)
                    except Exception:  # noqa: BLE001
                        continue
                    hit = [i["name"] for i in idx.get("directory", {}).get("item", [])
                           if re.search(r"ex-?99", i["name"], re.I)
                           and i["name"].endswith((".htm", ".html"))][:1]
                    if hit:
                        doc, accn, filed = hit[0], cand_accn, cand_filed
                        nodash = cand_nodash
                        break
                if doc is None:
                    gaps.append({"lei": lei, "form": form,
                                 "reason": f"no EX-99 in the last "
                                           f"{len(eights)} 8-K filings"})
                    continue
            else:
                if not primary or not primary.endswith((".htm", ".html")):
                    gaps.append({"lei": lei, "form": form,
                                 "reason": f"no HTML primary document "
                                           f"({primary or 'absent'})"})
                    continue
                doc = primary
            try:
                path = fetch(ARCHIVE.format(cik=cik, nodash=nodash, doc=doc),
                             manifest, f"{cik:010d}_{nodash}_{doc}", is_sec=True)
                raw = path.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:  # noqa: BLE001
                gaps.append({"lei": lei, "form": form,
                             "reason": f"fetch failed: {type(exc).__name__}"})
                continue

            ex = TextExtractor()
            ex.feed(raw)
            text = ex.text().translate(NORMALISE)

            for label, start_pat, end_pats in SECTIONS.get(form, [("exhibit_99", None, None)]):
                if start_pat is None:
                    body, off = text, 0
                else:
                    span = best_span(text, start_pat, end_pats)
                    if not span:
                        gaps.append({"lei": lei, "form": form, "section": label,
                                     "reason": "section heading not found"})
                        continue
                    st, en, bounded = span
                    if not bounded:
                        # Runs to the end of the filing: the named section plus
                        # everything after it. Recorded as a gap rather than
                        # stored, because a section that silently contains the
                        # rest of the document is worse than a missing one --
                        # it looks like unusually thorough coverage.
                        gaps.append({"lei": lei, "form": form, "section": label,
                                     "reason": "no end boundary found; span "
                                               f"would run {en - st:,} chars to "
                                               "end of filing — not stored"})
                        continue
                    off, body = st, text[st:en]
                if len(body) < MIN_SECTION_CHARS:
                    gaps.append({"lei": lei, "form": form, "section": label,
                                 "reason": f"section only {len(body)} chars — "
                                           "table-of-contents artefact or stub, "
                                           "not stored"})
                    continue
                records.append({
                    "document_id": f"{form}-{nodash}-{label}",
                    "lei": lei, "cik": cik, "sec_name": names.get(lei),
                    "accession": accn, "form": form, "section": label,
                    "filed_date": filed, "document": doc,
                    "source_offset": off, "text": body,
                    "text_length": len(body),
                    "provenance": "public", "source": "SEC EDGAR Archives",
                })
            print(f"  {names.get(lei, lei)[:26]:<28}{form:<6}"
                  f"{sum(1 for r in records if r['accession'] == accn)} section(s)")

    by_form: dict[str, int] = {}
    for r in records:
        by_form[f"{r['form']} {r['section']}"] = by_form.get(
            f"{r['form']} {r['section']}", 0) + 1
    print(f"\n  {len(records)} sections extracted")
    for k, v in sorted(by_form.items()):
        print(f"    {k:<24}{v:>4}")
    print(f"  {len(gaps)} gaps recorded (not invented)")
    reasons: dict[str, int] = {}
    for g in gaps:
        key = f"{g.get('form','?')} {g.get('section','-')}: {g['reason'][:52]}"
        reasons[key] = reasons.get(key, 0) + 1
    for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"    {v:>3}  {k}")
    if records:
        print(f"  median section length "
              f"{sorted(r['text_length'] for r in records)[len(records)//2]:,} chars")

    if args.dry_run:
        print("\n  DRY RUN — artifact not written.")
        return 0

    ARTIFACT.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "SEC EDGAR Archives — 10-K Item 1A/7, 10-Q Item 2, 8-K EX-99",
        "min_section_chars": MIN_SECTION_CHARS,
        "note": ("sections selected by largest span after the heading, never "
                 "first match, because a 10-K's table of contents repeats "
                 "every item heading and first-match returns the TOC row"),
        "section_count": len(records), "gaps": gaps, "documents": records,
    }, indent=2) + "\n")
    print(f"\n  wrote {ARTIFACT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
