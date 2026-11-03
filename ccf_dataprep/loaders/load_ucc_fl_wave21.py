#!/usr/bin/env python3
"""Wave 21 — load Florida UCC-1 filings into Fluree, and the debtor crosswalk
into Postgres.

`collateral-and-setoff-coverage` §C assigns lien filings and their filing dates
to **Fluree**, and the vault's own note of 2026-08-24 records the filing-date
row as never loaded:

    | Lien filing date | UCC-1 filing records -- **not loaded** | public | Fluree | R, T |

This loads it, for the MasTec family, from the Florida Secured Transaction
Registry. Terms bound in `docs/ccf_dataprep_v2.md` (Wave 21) BEFORE this write:
Fluree is append-only, so a name generated before it is bound cannot be
corrected, only contradicted.

## What this demonstrates, which is the point of loading it

§A's counterfactual:

    "A second-lien position recorded as 'secured' alongside a first-lien
     position recorded identically produces two facilities that look equally
     protected and are not."

The estate's lien priority is `synthetic -- engineered`, derived from EX-10
contract wording. It has no dates, so it cannot answer *when* a lien was
perfected -- and under UCC Article 9 the filing date is what decides priority
between competing secured parties.

The filed record answers it. Of the 65 filings loaded here, **13 carry a
Termination**: a lien a contract-derived column still calls "secured" and the
register says was released. That is a question no `first`/`second` column can
be asked.

## Single writer

Fluree is sole authority for every filing fact. Postgres receives ONLY the
filed-name -> LEI crosswalk, which is our claim about the filings rather than
a fact the registry asserts. No filing attribute is written to Postgres.

## Secured parties are keyed on the name AS FILED

24 distinct secured-party strings collapse to 23 under whitespace
normalisation. Normalising in place would erase the register's own evidence
that it holds two spellings. Each filed string gets its own node, keyed by a
hash of the exact bytes, with the exact string as a literal.

Run: uv run loaders/load_ucc_fl_wave21.py
     uv run loaders/load_ucc_fl_wave21.py --dry-run
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg  # noqa: E402

from ccf import config as C  # noqa: E402
from ccf import fluree  # noqa: E402

EX = "http://example.org/fibo/"
#: Dates are written as PLAIN ISO-8601 STRINGS, never as `^^xsd:date`.
#: This Fluree build corrupts xsd:date literals arriving through SPARQL
#: UPDATE: `"2024-12-19"^^xsd:date` reads back as `1971-11-15`, and across
#: 65 filings not one date survived, with 53 distinct deltas -- so it is
#: arbitrary, not a timezone or epoch offset. The identical value written
#: untyped round-trips exactly. See docs/known-issues.md §59.
#: Untyped is also the estate's existing convention: no other loader types
#: a date, which is why nothing hit this before.
XSD = "http://www.w3.org/2001/XMLSchema#"  # retained for non-date literals
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
SOURCE = Path(__file__).resolve().parent.parent / "sources" / "ucc_fl" / "mastec.json"
BATCH = 200

#: Above this, a filed debtor name is accepted as the same entity as a cast
#: legal name. Below it the row is still written, with the score, and the LEI
#: left NULL -- an unmatched debtor is a fact worth keeping, not a row to drop.
MATCH_ACCEPT = 0.90


def _uri(kind: str, key: str) -> str:
    return f"{EX}{kind}-{key}"


def _party_key(name: str) -> str:
    """Stable key for a secured-party name, preserving exact bytes.

    Hashed rather than slugified because the distinction that matters here is
    a TRAILING SPACE -- 'BANC OF AMERICA LEASING & CAPITAL, LLC' and the same
    string with one more character are two entries in the register, and any
    slug that strips whitespace would silently merge them and destroy the
    evidence.
    """
    return hashlib.sha1(name.encode()).hexdigest()[:12]


def _lit(v: str) -> str:
    return json.dumps(str(v))


def _date(v: str | None) -> str | None:
    """ISO date from the registry's timestamps, or None."""
    if not v:
        return None
    m = re.match(r"(\d{4}-\d{2}-\d{2})", v)
    return m.group(1) if m else None


def _norm(s: str) -> str:
    """Aggressive normalisation, used ONLY for scoring -- never stored."""
    s = s.upper()
    s = re.sub(r"[.,&]", " ", s)
    s = re.sub(r"\b(INC|LLC|LP|LLP|CORP|CORPORATION|COMPANY|CO|THE)\b", " ", s)
    return " ".join(s.split())


def build_triples(data: dict) -> list[str]:
    """Every triple this loader writes. Pure -- no I/O, so it is testable."""
    t: list[str] = []
    parties: dict[str, str] = {}

    for rec in data["debtors"]:
        f = _uri("ucc-filing", rec["ucc_number"])
        t.append(f"<{f}> a <{EX}UccFiling> .")
        t.append(f'<{f}> <{EX}filingNumber> {_lit(rec["ucc_number"])} .')
        t.append(f'<{f}> <{EX}filingStatus> {_lit(rec["status"])} .')
        t.append(f'<{f}> <{EX}documentType> {_lit(rec["document_type"])} .')
        t.append(f'<{f}> <{EX}debtorOfRecord> {_lit(rec["filed_debtor_name"])} .')

        fd = _date(rec["file_date"])
        if fd:
            t.append(f'<{f}> <{EX}filedOn> {_lit(fd)} .')
        # Written only where the registry supplies a value. A defaulted expiry
        # would make a filing with no stated lapse indistinguishable from one
        # that lapses today.
        ld = _date(rec["expiration_date"])
        if ld:
            t.append(f'<{f}> <{EX}lapsesOn> {_lit(ld)} .')

        for sp in rec["secured_parties"]:
            key = _party_key(sp["name"])
            uri = _uri("secured-party", key)
            if key not in parties:
                parties[key] = sp["name"]
                t.append(f"<{uri}> a <{EX}SecuredParty> .")
                # `rdfs:label` is the estate's existing display-label
                # predicate, so no new term is minted for this. The literal is
                # the exact filed string, trailing space and all -- that is
                # the whole point of hashing the key rather than slugifying it.
                t.append(f'<{uri}> <{RDFS}label> {_lit(sp["name"])} .')
            t.append(f"<{f}> <{EX}securedPartyOf> <{uri}> .")

        for am in rec["amendments"]:
            a = _uri("ucc-amendment", am["documentNumber"])
            t.append(f"<{a}> a <{EX}UccAmendment> .")
            t.append(f"<{f}> <{EX}amendedBy> <{a}> .")
            ad = _date(am.get("date"))
            if ad:
                t.append(f'<{a}> <{EX}filedOn> {_lit(ad)} .')
            for act in (am.get("actions") or []):
                if act.get("actionName"):
                    t.append(f'<{a}> <{EX}amendmentAction> '
                             f'{_lit(act["actionName"])} .')
    return t


def match_debtors(data: dict, conn) -> list[tuple]:
    """Score each filed debtor name against the cast's legal names.

    Uses `difflib.SequenceMatcher.ratio()`, never `quick_ratio()` -- the latter
    is an UPPER BOUND on the real ratio and will report matches that do not
    survive the full comparison.
    """
    cur = conn.cursor()
    cur.execute(f"select lei, legal_name from {C.PG_SCHEMA_V2}.legal_entity")
    cast = [(lei, name, _norm(name)) for lei, name in cur.fetchall()]

    rows = []
    seen = set()
    for rec in data["debtors"]:
        filed = rec["filed_debtor_name"]
        if filed in seen:
            continue
        seen.add(filed)
        target = _norm(filed)
        best_lei, best_name, best = None, None, 0.0
        for lei, name, ncast in cast:
            r = difflib.SequenceMatcher(None, target, ncast).ratio()
            if r > best:
                best_lei, best_name, best = lei, name, r
        accepted = best >= MATCH_ACCEPT
        rows.append((
            filed,
            best_lei if accepted else None,
            round(best, 4),
            "accepted" if accepted else "below_threshold",
            f"difflib.ratio on normalised names; nearest={best_name!r}",
            # CLAUDE.md defines exactly THREE provenance classes and
            # "derived" is not one of them -- `validators/large_exposure.py`
            # uses that very string as its example of an unrecognised label.
            # A crosswalk row is `synthetic -- internal`: deciding which filed
            # debtor is which client is a bank-internal act by nature, which
            # is why ccf_v2.crosswalk carries the same class for the
            # LEI<->internal_client_id mapping. The FILINGS stay `public`;
            # only our claim about them is synthetic.
            "synthetic — internal",
        ))
    return rows


DDL = """
create table if not exists {s}.ucc_debtor_crosswalk (
    filed_debtor_name text primary key,
    lei               text,
    match_score       numeric,
    match_band        text,
    match_method      text,
    provenance        text
)
"""


def load_postgres(rows: list[tuple], dry: bool) -> int:
    with psycopg.connect(**C.PG) as conn:
        cur = conn.cursor()
        cur.execute(f'set search_path to "{C.PG_SCHEMA_V2}", public')
        cur.execute(DDL.format(s=C.PG_SCHEMA_V2))
        if dry:
            conn.rollback()
            return 0
        for r in rows:
            cur.execute(
                f"""insert into {C.PG_SCHEMA_V2}.ucc_debtor_crosswalk
                    (filed_debtor_name, lei, match_score, match_band,
                     match_method, provenance)
                    values (%s,%s,%s,%s,%s,%s)
                    on conflict (filed_debtor_name) do update set
                      lei=excluded.lei, match_score=excluded.match_score,
                      match_band=excluded.match_band,
                      match_method=excluded.match_method,
                      provenance=excluded.provenance""", r)
        conn.commit()
        return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = json.loads(SOURCE.read_text())
    triples = build_triples(data)
    print(f"  {len(triples)} triples from {data['filings_retrieved']} filings")

    with psycopg.connect(**C.PG) as conn:
        rows = match_debtors(data, conn)
    accepted = sum(1 for r in rows if r[1])
    print(f"  {len(rows)} distinct filed debtor names, {accepted} matched to an LEI")

    if args.dry_run:
        print("  --dry-run: nothing written")
        for ln in triples[:6]:
            print("   ", ln)
        return 0

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")
    print(f"  Fluree: {len(triples)} triples written to {C.FLUREE_LEDGER_V2}")

    n = load_postgres(rows, dry=False)
    print(f"  Postgres: {n} crosswalk rows in {C.PG_SCHEMA_V2}.ucc_debtor_crosswalk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
