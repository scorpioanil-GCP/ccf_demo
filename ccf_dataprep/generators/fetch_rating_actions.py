#!/usr/bin/env python3
"""Wave 11a — paged rating-action sweep and Item 2.03 issuance events.

Two legs, one script (the design's §4 pipeline listed them separately; a
controller ruling merged them — both are EDGAR sweeps over the same 50 CIKs,
differing only in selection method).

## Leg 1: rating-action candidates (per-CIK-scoped full-text search)

§F condition 6 wants >= 1 obligor with a rating action disclosed in a real
8-K. Rating actions surface as Item 8.01 prose with no metadata flag to select
on, so this has to be full-text search.

**Two truncation bugs, found in sequence, both the same shape.** A
first-page-only sweep found 1 anchor; the identical sweep with paging (4
pages of 100) found 5 anchors across 14 filings and looked fixed. It was not:
a whole-corpus query for a common phrase like "S&P Global Ratings" runs to
~8,900 hits, of which 4 pages reads ~400 — about 10% — and which 10% depends
on EDGAR's internal result ordering, not on the data. 4-of-5 queries hit that
page cap on a real run. So this sweep queries EDGAR's own `ciks` scoping
parameter **per (CIK, query) pair** (see `sweep_rating_actions` and `cik10`)
instead of paging a whole-corpus query and filtering afterward — it still
calls `fts_pages()` (from `generators/screen_obligors.py`, Wave 0) for its
paging, so a single anchor's result set is itself never assumed to fit on one
page, but the query is now scoped to one filer at a time so "read more pages"
is never required to reach completeness against a corpus 200x the cast.

A hit only proves the agency's name appears in an 8-K — it could be a
downgrade, an affirmation, a new rated facility, or the name inside a defined
term. So every matched filing is fetched and searched for action language
(downgrade/upgrade/affirm/outlook/withdrawn/placed-on-watch, etc.) within a
bounded character window of the agency mention. A filing that clears that
bar is a **confirmed** rating action; one that doesn't is still a real filing
naming a rating agency, so it is recorded as a gap in `context_debt`
(`subject_kind='rating_action'`, `subject_key=accession`) rather than forced
into the dataset as something it isn't.

## Leg 2: Item 2.03 issuance (free — metadata only)

The EDGAR submissions index carries an `items` field per filing, so Item 2.03
selection is a string match on metadata, exactly like Wave 10's
`fetch_8k502.py` matched on "5.02". No document fetch: all 50 anchors have at
least one Item 2.03 filing (788 total across the cast), and Task 4 only needs
accession + filing date to anchor an engineered instrument's issue date to a
real filing.

Run:
    uv run generators/fetch_rating_actions.py --dry-run
    uv run generators/fetch_rating_actions.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.fetch import SourceManifest, fetch, get_json
from generators.fetch_def14a import strip_html
from generators.screen_obligors import fts_pages

SCREEN = REPO_ROOT / "sources" / "screening"

#: The task brief's exact query list. Each is a phrase/quote combination
#: chosen to bias toward the agency being the subject of the filing rather
#: than an incidental mention.
QUERIES = [
    '"Moody\'s Investors Service"',
    '"Standard & Poor\'s" "credit rating"',
    '"corporate credit rating"',
    '"S&P Global Ratings"',
    '"Fitch Ratings"',
]

#: A rating agency's name or a common abbreviation for it.
AGENCY_RE = re.compile(
    r"(Moody'?s(?:\s+Investors\s+Service)?"
    r"|Standard\s*&\s*Poor'?s"
    r"|S&P(?:\s+Global\s+Ratings)?"
    r"|Fitch(?:\s+Ratings)?)",
    re.I,
)

#: Round-1 defect, found by the reviewer reading cached text rather than
#: trusting labels: a bare verb stem ("downgrad\w*") within WINDOW chars of an
#: agency name matched a pricing-grid ratchet ("if S&P shall cease to assign a
#: Specified Rating, the Applicable Margin ... shall be based on Level III"),
#: a bare defined term ("'Downgrade Event' shall have the meaning ascribed to
#: in Section 2.7(b)"), and — worst — the NEGATION of an action ("there shall
#: not have been any downgrading") recorded as the action itself. All six of
#: round 1's AVIS "confirmations" were the same pricing-grid clause. None of
#: this needs new data to see; it was visible in the round-1 transcript
#: before the per-CIK fix, which only multiplied a broken test's output.
#:
#: REJECT_RE fires on the framing that produced every false positive above:
#: definitional ("means", "shall have the meaning"), conditional ("in the
#: event", "provided that"), pricing-grid/table ("Applicable Margin",
#: "Advance Rate", "Level I".."Level V", "pricing grid", "rating grid"), and
#: negated ("shall not have been", "no ... downgrading", "nor any", "will
#: not", "has/have not"). A match anywhere in the window rejects that window
#: outright — no positive pattern is even attempted — because a defined-term
#: or negated clause frequently ALSO contains a bare action verb (that is
#: exactly how it fooled the old regex), so the reject check must run first
#: and unconditionally.
REJECT_RE = re.compile(
    r"(\bmeans\b|shall\s+have\s+the\s+meaning|\bin\s+the\s+event\b"
    r"|\bprovided\s+that\b|\bapplicable\s+margin\b|\badvance\s+rate\b"
    r"|\blevel\s+[ivx]+\b|\bpricing\s+grid\b|\brating\s+grid\b"
    r"|shall\s+not\s+have\s+been|\bno\s+\w*\s*downgrad\w*|\bnor\s+any\b"
    r"|\bwill\s+not\b|\bhas\s+not\b|\bhave\s+not\b|\bshall\s+not\b)",
    re.I,
)

#: Requires a declarative, past-tense construction naming the action, not a
#: bare verb stem — "was downgraded", "downgraded ... to ... from ...",
#: "has assigned a ... rating", "announced that", "placed ... on watch",
#: "revised ... outlook to". Genuine rating-action prose (Vertiv, Celanese in
#: the confirmed set) reads this way; a defined term or pricing-grid clause
#: does not, even when REJECT_RE somehow misses it.
DECLARATIVE_RE = re.compile(
    r"(\bwas\s+(?:downgraded|upgraded|affirmed|lowered|raised|withdrawn)\b"
    r"|\bwere\s+(?:downgraded|upgraded|affirmed|lowered|raised|withdrawn)\b"
    r"|\bhas\s+(?:downgraded|upgraded|lowered|raised|affirmed|withdrawn|assigned)\b"
    r"|\bhave\s+(?:downgraded|upgraded|lowered|raised|affirmed|withdrawn|assigned)\b"
    r"|\b(?:downgraded|upgraded|lowered|raised)\b(?:\s+\S+){0,10}?\s+to\s+\S+\s+from\s+\S+"
    r"|\bannounced\s+that\b"
    r"|\bassigned\b\s+(?:a|an|its)\b[^.]{0,40}?\brating\b"
    r"|\bplaced\b[^.]{0,20}\bon\s+(?:credit\s*)?watch\b"
    r"|\brevised\b[^.]{0,20}\boutlook\b[^.]{0,20}\bto\b)",
    re.I,
)

#: Fix round 3 (coordinator-directed) removed a third gate that stood here —
#: DATE_RE, requiring a month/quarter/year token anywhere in the same
#: 300-char window as the declarative match. It was added on the theory that
#: a genuine rating action is a dated event where a defined term or
#: pricing-grid clause never is. In practice it tested proximity to the
#: AGENCY MENTION, not to the declarative clause itself, so it passed for
#: the wrong reason: all four Independence Realty Trust investor-presentation
#: rows ("Assigned a Long-Term Issuer Default Rating of 'BBB' ... from Fitch
#: Ratings") were "dated" only by an unrelated debt-maturity chart caption
#: ("...2024 2025 2026 2027 2028 Thereafter...") sitting elsewhere in the
#: window — not by any date attached to the sentence that actually confirmed
#: them.
#:
#: Two fixes were on the table: scope DATE_RE to a tight radius around the
#: declarative match instead of the whole window, or drop it. Tested both
#: against every cached candidate document: date-anywhere-in-window (the
#: original gate) and no-date-requirement-at-all produced the IDENTICAL
#: 9-row confirmed set — REJECT_RE and DECLARATIVE_RE alone already draw
#: that exact line, with zero rows differing either way. Proximity-scoping
#: (radius 100) instead REMOVED the four genuinely-true IRT rows, whose
#: declarative sentence has no date token near it at all (the deck's quarter
#: is established by its title, not repeated inline per bullet) — a real
#: rating action, confirmed as genuine on a direct read of the underlying
#: filing, would have been wrongly rejected. So the date gate was measured
#: to be pure dead weight here: it never distinguished a true positive from
#: a false one in this corpus, and its only effect under a proximity fix
#: would have been to manufacture a false negative. Dropped rather than
#: tightened. If a future corpus needs it, REJECT_RE + DECLARATIVE_RE should
#: be shown insufficient on real text first, the same way this file's whole
#: history has gone — measure before adding a gate, don't assume one.

#: Characters either side of an agency mention searched for action language.
#: Wide enough to span "Moody's ... downgraded the Company's rating to Ba2"
#: without also matching an unrelated action elsewhere in a long exhibit.
WINDOW = 300

#: The two `context_debt.reason` strings an unconfirmed candidate can be
#: recorded with. Module constants, NOT inline literals, because
#: `validators/artifact_reproduces_store.py` compares the live table against
#: them and must import the exact text rather than hold a frozen copy — a
#: copy is how this wave shipped a reason describing a gate that no longer
#: existed, twice (known-issues.md §9.1).
REASON_SEARCHED = (
    "candidate matched a rating-agency-name query but no declarative "
    "rating-action language survived the definition/condition/negation "
    f"filters within {WINDOW} chars of an agency mention in the fetched "
    "document(s); recorded as a gap, not asserted as an action")
REASON_UNSEARCHED = (
    "candidate matched a rating-agency-name query but every document fetch "
    "for this accession failed (see script output for the underlying "
    "error); no text was actually searched, so this is a fetch gap, not a "
    "negative content finding")

DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn}/{name}"


def _hit_matches_cik(ciks: list, cik: int) -> bool:
    """True if `cik` appears among a hit's `_source.ciks`, safely.

    A defensive re-check on top of the `ciks`-scoped query itself: a value
    EDGAR can't parse as an int should fail this check, not raise out of a
    generator expression and abort the sweep over one bad element.
    """
    for c in ciks:
        try:
            if int(c) == cik:
                return True
        except (TypeError, ValueError):
            continue
    return False


def confirm(text: str) -> str | None:
    """A declarative rating-action sentence within WINDOW chars of an agency
    mention — not merely a verb stem, and not a defined-term, conditional,
    pricing-grid, or negated one.

    Two gates, in order, both against the same window: REJECT_RE first
    (unconditional — a window that reads as a definition, a condition, a
    pricing table, or a negation is disqualified before any positive pattern
    is even tried, because round 1's false positives all *also* contained a
    bare action verb), then DECLARATIVE_RE (a real past-tense action
    construction — "was downgraded", "assigned a ... rating", "... to ...
    from ..." — not a stem). A third gate requiring a nearby date was tried
    and measured to add nothing: see the comment above DECLARATIVE_RE's
    removed neighbor for what was tested and why it was dropped rather than
    tightened.
    """
    for am in AGENCY_RE.finditer(text):
        lo, hi = max(0, am.start() - WINDOW), am.end() + WINDOW
        snippet = text[lo:hi]
        if REJECT_RE.search(snippet):
            continue
        decl = DECLARATIVE_RE.search(snippet)
        if not decl:
            continue
        start = max(0, decl.start() - 60)
        return snippet[start:decl.end() + 60].strip()
    return None


def load_anchors(cur) -> list[tuple[str, int]]:
    # ORDER BY: this feeds no RNG, but every SELECT in this project's history
    # that lacked one eventually became load-bearing to something that did.
    cur.execute(
        f'SELECT lei, cik FROM "{PG_SCHEMA_V2}".crosswalk '
        "WHERE cik IS NOT NULL ORDER BY lei"
    )
    return [(lei, int(cik)) for lei, cik in cur.fetchall()]


def cik10(cik: int) -> str:
    """Zero-pad a CIK to EDGAR's 10-digit `ciks` filter format.

    The unpadded form does not error — it silently returns zero results,
    which is indistinguishable from an anchor genuinely having none. Assert
    the shape rather than trust it, so a malformed value fails loudly here
    instead of shipping as a false "no rating actions for this anchor."
    """
    padded = f"{cik:010d}"
    assert len(padded) == 10 and padded.isdigit(), (
        f"cik10({cik!r}) produced {padded!r}, not a 10-digit numeric string"
    )
    return padded


def sweep_rating_actions(anchors: list[tuple[str, int]]) -> dict[tuple[int, str], dict]:
    """EDGAR FTS sweep, scoped per (CIK, query) — not a whole-corpus sweep.

    The first cut of this sweep ran each query unscoped and paged 4 pages of
    100 (400 hits) before moving to the next query. That is a page-4-only
    sweep wearing a page-1-only sweep's mistake: 4 of 5 queries hit that cap,
    against corpus totals up to ~8,900 for a single query — so ~90% of the
    matching corpus went unread, and which anchors turned up depended on
    EDGAR's internal result ordering rather than on the data. Raising `pages`
    further does not fix this in any reasonable budget (the biggest query
    would need ~89 pages), and it is the wrong shape regardless: our cast is
    50 filers out of roughly eight thousand, so reading the whole corpus to
    keep 0.1% of it is disproportionate at any depth.

    EDGAR FTS accepts its own `ciks` scoping parameter. Querying per (CIK,
    query) pair — 50 anchors x 5 queries = 250 requests — asks EDGAR for
    exactly our cast instead of filtering our cast out of everyone else's
    hits, so a query that would be an 8,900-hit, 90%-truncated whole-corpus
    read becomes a small, complete, per-anchor read. `pages=2` per pair is a
    safety margin, not an assumption: `fts_pages` still stops as soon as a
    page returns fewer than `size` hits, so it costs nothing when one page
    (as observed for every anchor in this cast) is enough, and it still pages
    correctly if a single anchor's hit count for one query ever exceeds 100.
    """
    candidates: dict[tuple[int, str], dict] = {}
    for lei, cik in anchors:
        cik_str = cik10(cik)
        for query in QUERIES:
            hits_seen = 0
            for hit in fts_pages(query, "8-K", pages=2, size=100, ciks=cik_str):
                hits_seen += 1
                src = hit.get("_source", {})
                ciks = src.get("ciks") or []
                # Belt-and-suspenders: confirm the hit actually names our CIK
                # rather than trusting that a `ciks`-scoped query can only
                # ever return it — a wrong-format or mismatched value should
                # fail to match here, not be silently accepted.
                if not _hit_matches_cik(ciks, cik):
                    continue
                file_date = src.get("file_date")
                accession = src.get("adsh")
                doc_id = hit.get("_id", "")
                filename = doc_id.split(":", 1)[1] if ":" in doc_id else None
                if not accession or not filename:
                    continue
                key = (cik, accession)
                cand = candidates.get(key)
                if cand is None:
                    cand = {
                        "lei": lei,
                        "cik": cik,
                        "accession": accession,
                        "file_date": file_date,
                        "matched_queries": [],
                        "documents": [],
                    }
                    candidates[key] = cand
                if query not in cand["matched_queries"]:
                    cand["matched_queries"].append(query)
                if filename not in cand["documents"]:
                    cand["documents"].append(filename)
            if hits_seen >= 100:
                # A single anchor produced a full first page on a query
                # scoped to just that CIK — unexpected for this cast size,
                # and worth a loud note even though fts_pages paged past it.
                print(f"    [note] {lei} {query[:40]!r}: {hits_seen} hits "
                      f"(>= a full page) for one CIK — verify pages=2 was "
                      f"enough")
        print(f"  {lei} (CIK {cik_str}): "
              f"{sum(1 for k in candidates if k[0] == cik)} candidate filing(s) so far")

    return candidates


def sweep_issuance(anchors: list[tuple[str, int]]) -> list[dict]:
    """Item 2.03 filings, selected by submissions-index metadata only.

    Reads ONLY `filings.recent`, which EDGAR caps at ~1000 filings per issuer
    and shards the remainder into `filings.files[]`. 40 of the 50 anchors have
    unread shards, so the returned list is a FLOOR on each issuer's Item 2.03
    history, not the complete public record. Nothing this wave depends on
    completeness here — Task 4 uses the two most recent filings per obligor and
    eligibility comes from `filing_profile` — but any consumer that treats this
    as exhaustive is wrong. Estate-wide pattern; see known-issues.md §9.
    """
    issuance: list[dict] = []
    for lei, cik in anchors:
        submissions = get_json(
            f"https://data.sec.gov/submissions/CIK{cik:010d}.json", is_sec=True)
        # EDGAR `recent`-only: the index caps at ~1000 filings per issuer and
        # shards the remainder into `filings.files[]`, which this sweep does NOT
        # read. 40 of the 50 anchors have unread shards, so results here are a
        # FLOOR on the issuer's history, never the complete public record.
        # Estate-wide pattern across 7 fetchers; see docs/known-issues.md §9.11.
        recent = submissions["filings"]["recent"]
        items = recent.get("items", [""] * len(recent["form"]))
        rows = [
            {"lei": lei, "cik": cik, "accession": a, "file_date": d, "items": it,
             "provenance": "public"}
            for f, a, d, it in zip(
                recent["form"], recent["accessionNumber"], recent["filingDate"],
                items, strict=True)
            if f == "8-K" and "2.03" in (it or "")
        ]
        issuance.extend(rows)
        print(f"  {lei} (CIK {cik}): {len(rows)} Item 2.03 filings")
    return issuance


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with pg_connect() as conn, conn.cursor() as cur:
        anchors = load_anchors(cur)
    print(f"{len(anchors)} anchors with a CIK\n")

    # Both sweeps are read-only GETs (fts_pages / get_json) — safe to run in
    # full under --dry-run so the reported counts are the real paged counts,
    # not a guess. Only document fetching, the context_debt write, and the
    # two output files are skipped in dry-run.
    print("Leg 1 — paged EDGAR FTS sweep for rating-action candidates")
    candidates = sweep_rating_actions(anchors)
    by_lei: dict[str, int] = {}
    for c in candidates.values():
        by_lei[c["lei"]] = by_lei.get(c["lei"], 0) + 1
    print(f"\n  {len(by_lei)} anchors, {len(candidates)} candidate filings")
    for lei, n in sorted(by_lei.items(), key=lambda kv: -kv[1]):
        print(f"    {lei}  {n} filing(s)")

    print("\nLeg 2 — Item 2.03 issuance filings (metadata only)")
    issuance = sweep_issuance(anchors)
    print(f"\n  {len(issuance)} Item 2.03 filings across "
          f"{len({r['lei'] for r in issuance})} anchors")

    if args.dry_run:
        print(f"\n  [dry-run] would fetch {len(candidates)} candidate 8-K "
              "documents to confirm rating-action language, then write "
              f"{(SCREEN / 'wave11a_rating_actions.json').relative_to(REPO_ROOT)} "
              f"and {(SCREEN / 'wave11a_issuance.json').relative_to(REPO_ROOT)}")
        return 0

    print("\nConfirming candidates against action-language in the filing text")
    manifest = SourceManifest(
        source="ratingactions8k",
        description="EDGAR 8-K filings matched by full-text search for a "
                     "rating-agency name, fetched to confirm action language",
        licence="US government work / public filing",
    )
    rating_actions: list[dict] = []
    debt_rows: list[tuple[str, str | None, str, str]] = []
    confirmed_accessions: list[str] = []
    confirmed_n = 0

    for (cik, accession), cand in sorted(candidates.items()):
        bare = accession.replace("-", "")
        evidence = None
        # Distinct from "confirmed": did we manage to fetch and search AT
        # LEAST ONE document for this candidate? If every fetch raises,
        # `evidence` stays None for a reason that has nothing to do with the
        # text — the old code folded that into the same "no action-language
        # was found in the fetched document(s)" reason used for a genuine
        # miss, which is false when nothing was fetched at all.
        searched_any = False
        for filename in cand["documents"]:
            url = DOC_URL.format(cik=cik, accn=bare, name=filename)
            fname = f"{cik:010d}_{bare}_{filename}"
            try:
                path = fetch(url, manifest, fname, is_sec=True)
                text = strip_html(path.read_text(encoding="utf-8", errors="replace"))
            except Exception as exc:  # noqa: BLE001 — a fetch failure is a
                # fact about one document, not grounds to abort the sweep.
                print(f"  [skip] {fname}: {type(exc).__name__} {str(exc)[:60]}")
                continue
            searched_any = True
            hit = confirm(text)
            if hit:
                evidence = hit
                break

        record = {
            "lei": cand["lei"],
            "cik": cik,
            "accession": accession,
            "file_date": cand["file_date"],
            "matched_query": "; ".join(cand["matched_queries"]),
            "documents": cand["documents"],
            "confirmed": evidence is not None,
            "provenance": "public",
        }
        if evidence:
            record["evidence"] = evidence
            confirmed_n += 1
            confirmed_accessions.append(accession)
            print(f"  [confirmed] {cand['lei']} {accession}  \"{evidence[:70]}...\"")
        else:
            reason = REASON_SEARCHED if searched_any else REASON_UNSEARCHED
            record["reason"] = reason
            record["searched"] = searched_any
            debt_rows.append((accession, None, reason, accession))
            print(f"  [unconfirmed] {cand['lei']} {accession} -> context_debt"
                  f"{'' if searched_any else '  (fetch failed, not searched)'}")
        rating_actions.append(record)

    print(f"\n  {confirmed_n}/{len(candidates)} candidates confirmed")

    if debt_rows or confirmed_accessions:
        # No DDL here: the constraint on this script is read-only except
        # idempotent context_debt INSERTs, and CREATE INDEX is neither. The
        # partial unique index (ux_context_debt_subject) was already created
        # by loaders/load_postgres_wave10.py's schema migration; this script
        # only ever relies on it, never (re-)issues it.
        with pg_connect() as conn, conn.cursor() as cur:
            if confirmed_accessions:
                # Reconcile, don't just append. A confirmation heuristic can
                # get stricter (or looser) between runs — this one just did,
                # sharply — so an accession `context_debt` recorded as an
                # unconfirmed gap on an earlier run can legitimately become
                # confirmed on a later one without ever changing on disk. A
                # stale gap row for something we now have positive evidence
                # for is not a harmless leftover: it asserts "no action-
                # language was found" about a document that, re-read, turned
                # out to contain exactly that. Delete it rather than let two
                # runs of the same script disagree with each other in the
                # store.
                cur.execute(
                    f'DELETE FROM "{PG_SCHEMA_V2}".context_debt '
                    "WHERE subject_kind = 'rating_action' "
                    "AND subject_key = ANY(%s)",
                    (confirmed_accessions,),
                )
                if cur.rowcount:
                    print(f"  {cur.rowcount} stale context_debt row(s) "
                          f"removed — now-confirmed on this run")
            if debt_rows:
                cur.executemany(
                    f'INSERT INTO "{PG_SCHEMA_V2}".context_debt '
                    "(accession, covenant_type, reason, recorded_at, "
                    "subject_kind, subject_key) VALUES "
                    "(%s,%s,%s,current_date,'rating_action',%s) "
                    # NOT a bare ON CONFLICT DO NOTHING any more (that was
                    # the Wave 10-precedent form, and it is what left 134 of
                    # 169 rows carrying reason text from a superseded regex
                    # round across three fix rounds — see known-issues.md
                    # §9.1). DO UPDATE needs an explicit conflict target, and
                    # because ux_context_debt_subject is a PARTIAL unique
                    # index, the target must repeat its own WHERE predicate
                    # for Postgres to infer it as the arbiter. subject_kind
                    # is always the literal 'rating_action' here, so this
                    # can only ever match an existing rating_action row —
                    # Wave 10's subject_kind='person' rows share the index
                    # but never the subject_kind value, so they cannot be
                    # touched by this statement.
                    "ON CONFLICT (subject_kind, subject_key) "
                    "WHERE subject_kind IS NOT NULL "
                    "DO UPDATE SET reason = EXCLUDED.reason",
                    debt_rows,
                )
            conn.commit()
        if debt_rows:
            print(f"  {len(debt_rows)} unconfirmed candidates recorded in "
                  f"context_debt (subject_kind='rating_action')")

    (SCREEN / "wave11a_rating_actions.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "SEC EDGAR full-text search (efts.sec.gov), paged",
        "queries": QUERIES,
        "window_chars": WINDOW,
        "candidate_count": len(rating_actions),
        "confirmed_count": confirmed_n,
        "rating_actions": rating_actions,
    }, indent=2) + "\n")

    (SCREEN / "wave11a_issuance.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "SEC EDGAR submissions index, items field (metadata only, "
                   "no document fetch)",
        "filing_count": len(issuance),
        "issuance": issuance,
    }, indent=2) + "\n")

    print(f"\n  written: {(SCREEN / 'wave11a_rating_actions.json').relative_to(REPO_ROOT)}")
    print(f"  written: {(SCREEN / 'wave11a_issuance.json').relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
