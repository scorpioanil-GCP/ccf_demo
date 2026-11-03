#!/usr/bin/env python3
"""Wave 0 — screen candidate anchor obligors against the §F condition union.

The §F envelopes do not ask for 21 independent samples. They ask the *same*
~50 anchor obligors to jointly satisfy conditions scattered across every spec.
Selecting per-product yields overlapping-but-disjoint sets and five stores that
cannot be assembled. This screens condition-first so every `>= N` is
satisfiable by construction.

Conditions screened here (EDGAR-derived only; GLEIF and XBRL conditions are
scored in later stages):

    C1  EX-10 credit agreement with financial-covenant language
    C2  guarantor schedule present in the same exhibit
    C3  defined-terms article ("as defined in Section")
    C4  >= 1 filed amendment (8-K Item 1.01 with an EX-10)
    C5  8-K Item 2.04 — acceleration/breach — in filing history
    C6  non-December fiscal year end

Output: sources/screening/candidates.json — every candidate annotated with
which conditions it satisfies and the accession numbers evidencing each.
Nothing is loaded. The list is a proposal for review.

Run: uv run generators/screen_obligors.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from urllib.parse import urlencode

from ccf.config import REPO_ROOT
from ccf.fetch import get_json

FTS = "https://efts.sec.gov/LATEST/search-index?"
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

# Screening window. Recent enough that filings are in EDGAR full-text search
# (2001+) and that the agreements resemble current market practice.
START = "2022-01-01"
END = "2026-08-01"

#: Every EDGAR fetch that raised during a screening run, recorded rather than
#: swallowed, across BOTH fetch stages: the full-text page sweep and the
#: fiscal-year-end enrichment. A failed fetch is silent data loss in each case
#: -- a short page result is indistinguishable from a genuinely small one, and
#: a candidate whose submissions fetch failed keeps `fiscal_year_end = ""`,
#: which is indistinguishable from a real December year-end and so silently
#: withholds `C6_non_dec_fye` and shifts the condition-count ranking.
#: main() refuses to write the artifact when this is non-empty, so a partial
#: screen can never be mistaken for a complete one.
#:
#: Cleared at the top of main() -- module state that is never reset makes the
#: gate sticky for the process lifetime, so a second call in the same process
#: would refuse to write even after a clean run.
FETCH_FAILURES: list[dict] = []


@dataclass
class Candidate:
    cik: int
    name: str
    ticker: str = ""
    sic: str = ""
    inc_state: str = ""
    biz_state: str = ""
    conditions: set[str] = field(default_factory=set)
    evidence: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    fiscal_year_end: str = ""

    def note(self, condition: str, accession: str) -> None:
        self.conditions.add(condition)
        if accession not in self.evidence[condition]:
            self.evidence[condition].append(accession)

    def as_dict(self) -> dict:
        return {
            "cik": self.cik,
            "name": self.name,
            "ticker": self.ticker,
            "sic": self.sic,
            "inc_state": self.inc_state,
            "biz_state": self.biz_state,
            "fiscal_year_end": self.fiscal_year_end,
            "conditions": sorted(self.conditions),
            "condition_count": len(self.conditions),
            "evidence": {k: v[:4] for k, v in self.evidence.items()},
        }


NAME_RE = re.compile(r"^(?P<name>.*?)\s+\((?P<ticker>[^)]*)\)\s+\(CIK (?P<cik>\d+)\)")


def parse_display(display: str) -> tuple[str, str] | None:
    m = NAME_RE.match(display)
    if not m:
        return None
    return m.group("name").strip(), m.group("ticker").strip()


def fts_pages(query: str, forms: str, *, pages: int = 4, size: int = 100,
              ciks: str | None = None):
    """Iterate EDGAR full-text search hits, paging through `from` offsets.

    `ciks` (optional) is EDGAR's own scoping parameter — a comma-separated
    list of zero-padded 10-digit CIKs. Passing it turns a whole-corpus query
    into a query against a named set of filers, which is what makes a small
    cast safe to sweep exhaustively: a whole-corpus query for a common phrase
    can run into the tens of thousands of hits, of which `pages * size` reads
    only a slice, and the slice is not guaranteed stable across runs. Scoped
    to the filers we actually care about, the same query returns a number of
    hits proportional to the cast, not to the corpus.

    Every query is bounded by the module-level `START`/`END` window, which is
    NOT a parameter: callers cannot widen or narrow it per query, and a hit
    outside those dates is invisible to every caller. Change the constants to
    change the screen.

    A page whose fetch raises is appended to `FETCH_FAILURES` and iteration
    stops for that query — the partial hits already yielded are kept, because
    they are real, but main() will refuse to write the artifact.
    """
    for page in range(pages):
        params = {
            "q": query,
            "forms": forms,
            "startdt": START,
            "enddt": END,
            "from": page * size,
        }
        if ciks:
            params["ciks"] = ciks
        try:
            data = get_json(FTS + urlencode(params), is_sec=True)
        except Exception as exc:  # noqa: BLE001 - recorded below, not swallowed
            print(f"    page {page}: {type(exc).__name__} {str(exc)[:60]}")
            FETCH_FAILURES.append({
                "stage": "fts_page", "what": f"page {page} of {query[:56]!r}",
                "error": f"{type(exc).__name__}: {str(exc)[:200]}",
            })
            return
        hits = data.get("hits", {}).get("hits", [])
        if not hits:
            return
        yield from hits
        if len(hits) < size:
            return


def screen(candidates: dict[int, Candidate], query: str, condition: str,
           *, forms: str = "8-K", require_ex10: bool = True,
           require_item: str | None = None, pages: int = 4) -> None:
    print(f"  [{condition}] {query[:64]}")
    found = 0
    for hit in fts_pages(query, forms, pages=pages):
        src = hit.get("_source", {})
        file_type = (src.get("file_type") or "")
        if require_ex10 and not file_type.upper().startswith("EX-10"):
            continue
        if require_item and require_item not in (src.get("items") or []):
            continue
        for display in src.get("display_names", []):
            parsed = parse_display(display)
            if not parsed:
                continue
            name, ticker = parsed
            ciks = src.get("ciks") or []
            if not ciks:
                continue
            cik = int(ciks[0])
            cand = candidates.get(cik)
            if cand is None:
                cand = Candidate(cik=cik, name=name, ticker=ticker)
                candidates[cik] = cand
            sics = src.get("sics") or []
            if sics and not cand.sic:
                cand.sic = sics[0]
            inc = src.get("inc_states") or []
            if inc and not cand.inc_state:
                cand.inc_state = inc[0]
            biz = src.get("biz_states") or []
            if biz and not cand.biz_state:
                cand.biz_state = biz[0]
            cand.note(condition, src.get("adsh", ""))
            found += 1
    print(f"      -> {found} hits")


def enrich_fiscal_year_end(candidates: dict[int, Candidate], limit: int) -> None:
    """Pull fiscal year end from the submissions API for top candidates."""
    ranked = sorted(
        candidates.values(), key=lambda c: len(c.conditions), reverse=True
    )[:limit]
    print(f"\n  Fetching fiscal year end for top {len(ranked)} candidates...")
    for cand in ranked:
        try:
            sub = get_json(SUBMISSIONS.format(cik=cand.cik), is_sec=True)
        except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
            # Swallowing this leaves `fiscal_year_end = ""`, which reads as a
            # December year-end and silently withholds C6 -- the same
            # complete-looking partial result the page gate exists to prevent.
            print(f"    CIK {cand.cik} ({cand.name[:40]}): "
                  f"{type(exc).__name__} {str(exc)[:60]}")
            FETCH_FAILURES.append({
                "stage": "fiscal_year_end", "what": f"CIK {cand.cik} {cand.name[:40]}",
                "error": f"{type(exc).__name__}: {str(exc)[:200]}",
            })
            continue
        fye = sub.get("fiscalYearEnd") or ""
        cand.fiscal_year_end = fye
        if not cand.sic:
            cand.sic = str(sub.get("sic") or "")
        if fye and not fye.startswith("12"):
            cand.note("C6_non_dec_fye", f"FYE={fye}")


def _abort_incomplete() -> int:
    """Report every recorded fetch failure and refuse to write. Always 1."""
    print(f"\n  [FAIL] {len(FETCH_FAILURES)} EDGAR fetch(es) failed; the "
          "screen is incomplete and NOTHING was written.")
    for f in FETCH_FAILURES:
        print(f"    [{f['stage']}] {f['what']}: {f['error']}")
    print("  Re-run once EDGAR is reachable; screening is idempotent.")
    return 1


def main() -> int:
    candidates: dict[int, Candidate] = {}
    FETCH_FAILURES.clear()

    print("EDGAR full-text screening")
    print(f"  window: {START} .. {END}\n")

    # C1 — financial covenant language in an EX-10 credit agreement.
    screen(candidates,
           '"Consolidated Leverage Ratio" "Interest Coverage Ratio"',
           "C1_financial_covenants")

    # C2 — guarantor schedule alongside covenant language.
    screen(candidates,
           '"Consolidated Leverage Ratio" "Subsidiary Guarantors"',
           "C2_guarantor_schedule")

    # C3 — defined-terms cross-reference, the covenant-cross-reference anchor.
    screen(candidates,
           '"as defined in Section" "Consolidated EBITDA"',
           "C3_defined_terms")

    # C4 — amendment: 8-K Item 1.01 carrying an amended credit agreement.
    screen(candidates,
           '"Amendment No" "Credit Agreement"',
           "C4_amendment", require_item="1.01")

    # C5 — 8-K Item 2.04, acceleration or breach. Rare and high-value:
    # covenant-in-force-as-of needs >= 2 obligors carrying one.
    screen(candidates,
           '"Credit Agreement"',
           "C5_item_2_04", require_ex10=False, require_item="2.04", pages=6)

    print(f"\n  {len(candidates)} distinct candidates discovered")

    # Fail fast. The run is already guaranteed to write nothing, so issuing
    # ~60 further requests against a host that is unreachable or rate-limiting
    # is pure waste and, under a rate limit, deepens the backoff.
    if FETCH_FAILURES:
        return _abort_incomplete()

    enrich_fiscal_year_end(candidates, limit=60)

    ranked = sorted(
        candidates.values(),
        key=lambda c: (len(c.conditions), c.name),
        reverse=True,
    )

    if FETCH_FAILURES:
        return _abort_incomplete()

    out_dir = REPO_ROOT / "sources" / "screening"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "candidates.json"
    out_path.write_text(
        json.dumps(
            {
                "generated_for": "Wave 0 obligor screening",
                "window": {"start": START, "end": END},
                "source": "SEC EDGAR full-text search (efts.sec.gov)",
                "condition_legend": {
                    "C1_financial_covenants": "EX-10 with leverage + interest coverage covenants",
                    "C2_guarantor_schedule": "EX-10 naming subsidiary guarantors",
                    "C3_defined_terms": "defined-terms cross-reference in EX-10",
                    "C4_amendment": "8-K Item 1.01 with amended credit agreement",
                    "C5_item_2_04": "8-K Item 2.04 acceleration/breach event",
                    "C6_non_dec_fye": "fiscal year end is not December",
                },
                "candidate_count": len(ranked),
                "candidates": [c.as_dict() for c in ranked],
            },
            indent=2,
        )
        + "\n"
    )

    print(f"\n  written: {out_path.relative_to(REPO_ROOT)}")
    print("\n  Condition coverage across pool:")
    coverage: dict[str, int] = defaultdict(int)
    for cand in ranked:
        for cond in cand.conditions:
            coverage[cond] += 1
    for cond in sorted(coverage):
        print(f"    {cond:26s} {coverage[cond]:>4} candidates")

    print("\n  Top 15 by condition count:")
    for cand in ranked[:15]:
        conds = ",".join(sorted(c.split("_")[0] for c in cand.conditions))
        print(f"    {len(cand.conditions)}  {cand.name[:40]:42s} {cand.ticker:6s} {conds}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
