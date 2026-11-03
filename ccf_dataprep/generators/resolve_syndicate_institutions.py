#!/usr/bin/env python3
"""Wave 18 Task 3 — schedule lender names -> real LEI and RSSD.

§C: "Co-lender institution identities | FFIEC NIC RSSD; GLEIF LEI | public
| Postgres". Filed schedules name institutions in a dozen spellings
("JPMorgan Chase Bank, N.A." / "JPMORGAN CHASE BANK, N.A." /
"JPMorgan Chase Bank, National Association"); all must collapse to ONE
member carrying ONE real LEI, or Task 8's edges attach to phantom members.

member_id is sha256(lei)[:8], NOT a row index. See CLAUDE.md and
docs/known-issues.md on positional identity.

Pattern reused from generators/fetch_reporting_bank.py: FDIC BankFind for
RSSD/Call Report data, GLEIF for LEI. That script resolves one bank; this
one groups 58 filed lender_raw strings (six commitment schedules, from
sources/screening/wave18_schedules.json) into 45 distinct institutions —
40 resolved to a real LEI (several of them funds or insurers that were
never going to have an RSSD at all; RSSD is a US bank-regulatory
identifier, never invented for a foreign branch or non-bank entity), 5
more real filed institutions with NO discoverable real LEI (small
single-deal co-investment vehicles — Ruling T3-R1, coordinator, after
independently re-verifying the GLEIF search: these become members with
lei=None and a no_lei_reason, never dropped and never given a SYN-
synthetic identifier), and the one corrupt string below, which stays in
manual_review because it is not a real, resolvable institution at all.

Two rulings baked in here, both from the task brief:

1. Name-variant collapsing is NOT left to fuzzy matching. Raw lender
   strings are grouped by `canonical_key()` — a deterministic normalise()
   plus a tiny, explicit ALIASES table for the handful of short forms
   (\"Truist\" -> \"Truist Bank\", branch-suffixed names -> their parent
   legal entity) that normalise() alone cannot bridge. Every merge this
   produces is enumerated in the printed report so it can be eyeballed,
   not just counted.

2. "BarclaysFifth Third Bank PLC, National Association" is excluded from
   grouping entirely, before normalise() ever sees it. It is two real
   institutions (Barclays Bank PLC and Fifth Third Bank, National
   Association) interleaved at word level by a filing redline artifact
   that cannot be reconstructed. It is written to `manual_review` with an
   explicit reason and is NEVER a candidate for GLEIF/FDIC lookup — an
   automated resolver could easily "succeed" at matching it to one of the
   two real banks it contains, which would be worse than failing loudly.

Any name that resolves to zero or more than one real, ACTIVE GLEIF LEI is
also routed to `manual_review` and printed loudly. The task is not done
while that list holds anything other than the corrupt string above — see
MANUAL_LEI below for the by-hand resolutions this run required.

Output: sources/screening/wave18_institutions.json

    uv run generators/resolve_syndicate_institutions.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from urllib.parse import quote

from ccf.config import REPO_ROOT
from ccf.fetch import get_json

SCREEN = REPO_ROOT / "sources" / "screening"
SCHEDULES = SCREEN / "wave18_schedules.json"
OUT = SCREEN / "wave18_institutions.json"

GLEIF = "https://api.gleif.org/api/v1/lei-records"
FDIC = "https://api.fdic.gov/banks"

RETRIEVED_AT = "2026-08-25"

#: This exact string is two institutions interleaved word-by-word by a
#: filing redline. Task 2 deliberately left it malformed. It must never be
#: fuzzy-matched — picking either bank invents a lender relationship no
#: filing states, and picking both invents an amount split.
CORRUPT_RAW = "BarclaysFifth Third Bank PLC, National Association"
CORRUPT_REASON = (
    "Two institutions (Barclays Bank PLC and Fifth Third Bank, National "
    "Association) interleaved at word level by a filing redline artifact "
    "that cannot be reconstructed without the source document's CSS. "
    "Never fuzzy-matched to either bank per CLAUDE.md's rule against "
    "inventing a lender relationship no filing states.")

# ---------------------------------------------------------------------------
# Name collapsing
# ---------------------------------------------------------------------------

#: A branch designation is an operating detail of a legal entity, not a
#: different entity — "MUFG Bank, Ltd., Canada Branch" and "..., Chiba
#: Branch" carry the same LEI. Stripped only when trailing, so it can't eat
#: into an unrelated word earlier in the name.
_BRANCH_SUFFIX_RE = re.compile(
    r",?\s+(CANADA|CANADIAN|CHIBA|NEW YORK|LONDON|TOKYO|HONG KONG)\s+BRANCH$"
)

#: Short forms normalise() cannot bridge on its own, verified by hand
#: against the full-form spelling that appears elsewhere in the same
#: schedules. Each entry is a DELIBERATE collapse, not a fuzzy guess —
#: see the module docstring.
ALIASES = {
    "TRUIST": "TRUIST BANK",
    "PNC BANK": "PNC BANK NATIONAL ASSOCIATION",
}


def _strip_diacritics(s: str) -> str:
    """"Bank of Montréal" and "Bank of Montreal" must normalise identically —
    GLEIF's own registered spelling keeps the accent, the filed schedule
    doesn't. NFKD-decompose and drop combining marks rather than leaving an
    accented letter to be blown away as punctuation by the regex below,
    which would silently break the token instead of just losing the accent.
    """
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def normalise(name: str) -> str:
    """Uppercase, drop punctuation, expand N.A./NA <-> NATIONAL ASSOCIATION,
    drop trailing branch designations."""
    s = _strip_diacritics(name).upper()
    s = s.replace(".", "").replace(",", "")
    s = re.sub(r"[^A-Z0-9\s]", " ", s)  # hyphens, &, remaining punctuation -> space
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\bNA\b", "NATIONAL ASSOCIATION", s)
    s = _BRANCH_SUFFIX_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def canonical_key(name: str) -> str:
    n = normalise(name)
    return ALIASES.get(n, n)


# ---------------------------------------------------------------------------
# Manual resolutions — looked up by hand against gleif.org, not guessed
# ---------------------------------------------------------------------------

#: Populated only for a canonical_key() that the automated GLEIF pass
#: resolves to zero or more than one ACTIVE record. Each entry names the
#: gleif.org search actually performed and today's retrieval date, per
#: CLAUDE.md's sanctioned path ("resolving by hand, against gleif.org, with
#: the retrieval date recorded beside it ... is not guessing; it is
#: sourcing"). Keyed by canonical_key().
MANUAL_LEI: dict[str, dict] = {
    # GLEIF returns two ACTIVE exact-name matches for "Canadian Imperial
    # Bank Of Commerce": the Canadian parent (CA) and a US-registered
    # record for the same bank's US branch operations. The schedule lists
    # CIBC as a syndicate lender alongside RBC, Scotiabank and TD in a
    # Canadian-obligor facility (agreement 1046102) — the parent entity is
    # the correct lender of record, not a US branch registration.
    "CANADIAN IMPERIAL BANK OF COMMERCE": {
        "lei": "2IGI19DL77OX0HC3ZE78",
        "legal_name": "Canadian Imperial Bank of Commerce",
        "category": "GENERAL",
        "note": "Canadian parent (category GENERAL) chosen over "
                "549300H8L46OOZOFHU82, a category BRANCH record "
                "(legalAddress Boston, US) under the identical name; "
                "confirmed against entity.category after the Bank of "
                "America / Citibank fix, in addition to the original "
                "jurisdiction (CA) reasoning.",
        "source": f"{GLEIF}/2IGI19DL77OX0HC3ZE78",
        "retrieved_at": RETRIEVED_AT,
    },
    # CORRECTED after coordinator review: the entry originally here bound
    # to 254900UJSGYIL5JU7B49, which is a BRANCH-category record (legal
    # address Jakarta, ID) — one of Bank of America's own branch
    # registrations, not the chartered entity. It read as correct because
    # headquartersAddress says Charlotte on that record too: every branch
    # carries its parent's HQ address by definition, so that field cannot
    # discriminate between an entity and any of its branches. The
    # discriminating field is entity.category (GENERAL vs BRANCH) plus
    # legalAddress. B4TYDEB6GKMZO031MB27 is category GENERAL with
    # legalAddress Charlotte, NC — the actual chartered bank. It did not
    # rank inside the original page[size]=10 GLEIF query for "Bank of
    # America, N.A."; it does appear once page size is 20 or the query is
    # "Bank of America National Association".
    "BANK OF AMERICA NATIONAL ASSOCIATION": {
        "lei": "B4TYDEB6GKMZO031MB27",
        "legal_name": "Bank Of America, National Association",
        "category": "GENERAL",
        "note": "GENERAL-category entity record, legalAddress Charlotte NC "
                "— the chartered bank, not a branch registration. Three "
                "ACTIVE exact-name matches exist in GLEIF: this one "
                "(GENERAL, US-NC), a BRANCH-category Jakarta registration "
                "(254900UJSGYIL5JU7B49, wrongly bound here originally), "
                "and a GENERAL Argentina-registered record "
                "(579100KKDIKGFCKKF068) under the identical name.",
        "source": f"{GLEIF}/B4TYDEB6GKMZO031MB27",
        "retrieved_at": RETRIEVED_AT,
    },
    # NEW after coordinator review, same defect class as Bank of America
    # above: the automated resolver's ORIGINAL pass found exactly one
    # ACTIVE exact-name match for "Citibank N.A." — 984500E7FX6880WAFF95
    # — and silently accepted it, because it was the only candidate
    # under that query text and nothing checked its category. It is a
    # BRANCH-category record (legalAddress Jakarta, ID). The chartered
    # entity is "Citibank, National Association" (comma, full form),
    # category GENERAL, legalAddress Sioux Falls, SD — which also
    # matches the BRANCH record's own headquartersAddress (Sioux Falls),
    # confirming it is that record's actual head office. Cross-checked
    # against FDIC BankFind: CERT 7213, RSSD 476810, identical legal name,
    # ACTIVE.
    "CITIBANK NATIONAL ASSOCIATION": {
        "lei": "E57ODZWZ7FF32TWEFA76",
        "legal_name": "Citibank, National Association",
        "category": "GENERAL",
        "note": "GENERAL-category entity record, legalAddress Sioux Falls "
                "SD. Replaces 984500E7FX6880WAFF95, a BRANCH-category "
                "Jakarta registration the original automated pass accepted "
                "as the sole ACTIVE exact match under the query text "
                "'Citibank N.A.' without checking category.",
        "source": f"{GLEIF}/E57ODZWZ7FF32TWEFA76",
        "retrieved_at": RETRIEVED_AT,
    },
    # Two exact ACTIVE "Barclays Bank PLC" records in GB. Disambiguated by
    # each record's own `registeredAs` company number: G5GSEF7VJP5I7OUK5573
    # carries 01026167, Barclays Bank PLC's real UK Companies House number;
    # the other (2549003Q5J2G7ALNU316) carries a different registration.
    "BARCLAYS BANK PLC": {
        "lei": "G5GSEF7VJP5I7OUK5573",
        "legal_name": "Barclays Bank PLC",
        "category": "GENERAL",
        "note": "Chosen over 2549003Q5J2G7ALNU316 by UK company number: "
                "01026167 is Barclays Bank PLC's real Companies House "
                "number; the other record registers as 68S01191.",
        "source": f"{GLEIF}/G5GSEF7VJP5I7OUK5573",
        "retrieved_at": RETRIEVED_AT,
    },
    # normalise() strips the accent from "Montréal", so GLEIF's own
    # accented spelling never matched the filed "Bank of Montreal" before
    # this MANUAL_LEI entry was added; kept explicit anyway since it is a
    # single-candidate group and cheap to pin down.
    "BANK OF MONTREAL": {
        "lei": "NQQ6HPCNCCU6TUTQYE16",
        "legal_name": "Bank of Montreal",
        "category": "GENERAL",
        "note": "GLEIF's own record spells it 'Bank of Montréal' (CA-QC, "
                "the Canadian parent) — the only ACTIVE candidate whose "
                "name is otherwise identical to the other nine "
                "Bank-of-Montreal-branded GLEIF records (holding co, "
                "mortgage corp, pension funds, European PLC).",
        "source": f"{GLEIF}/NQQ6HPCNCCU6TUTQYE16",
        "retrieved_at": RETRIEVED_AT,
    },
    # Two ACTIVE "Goldman Sachs Bank USA" records: the US bank itself and
    # its London Branch, filed under the same legal name. The US entity is
    # the lender of record for every schedule row naming this bank.
    "GOLDMAN SACHS BANK USA": {
        "lei": "KD3XUN7C6T14HNAYLU02",
        "legal_name": "Goldman Sachs Bank USA",
        "category": "GENERAL",
        "note": "US entity chosen over 98450079EAMB14EF3964 (GOLDMAN SACHS "
                "BANK USA LONDON BRANCH), filed under the identical legal "
                "name.",
        "source": f"{GLEIF}/KD3XUN7C6T14HNAYLU02",
        "retrieved_at": RETRIEVED_AT,
    },
    # "Goldman Sachs Lending Partners" (no suffix) is not the registered
    # legal name — GLEIF's only candidate under this name adds "LLC".
    "GOLDMAN SACHS LENDING PARTNERS": {
        "lei": "5X7O2M1I3LNNJ4E5R997",
        "legal_name": "Goldman Sachs Lending Partners LLC",
        "category": "GENERAL",
        "note": "Sole ACTIVE GLEIF match; the schedule's spelling drops "
                "the 'LLC' the registered legal name carries.",
        "source": f"{GLEIF}/5X7O2M1I3LNNJ4E5R997",
        "retrieved_at": RETRIEVED_AT,
    },
    # "M&T Bank" is the trade name. The chartered legal entity is still
    # named for its 1856 predecessor, Manufacturers and Traders Trust
    # Company — GLEIF has no LEI at all under "M&T Bank, National
    # Association"; confirmed against FDIC BankFind (CERT 588,
    # RSSD 501105) under the same legal name.
    "M T BANK NATIONAL ASSOCIATION": {
        "lei": "WWB2V0FCW3A0EE3ZJN75",
        "legal_name": "Manufacturers and Traders Trust Company",
        "category": "GENERAL",
        "note": "'M&T Bank' is a trade name, not the registered legal "
                "name. Cross-checked against FDIC BankFind, which lists "
                "the identical legal name at CERT 588 / RSSD 501105.",
        "source": f"{GLEIF}/WWB2V0FCW3A0EE3ZJN75",
        "retrieved_at": RETRIEVED_AT,
    },
    # Neither MUFG Bank, Ltd. nor Mizuho Bank, Ltd. resolve by name search
    # at all — GLEIF registers each under its Japanese legal name only
    # (English is an ALTERNATIVE_LANGUAGE_LEGAL_NAME on the SAME record,
    # not a separately searchable one). Found instead via each entity's
    # own `head-office` relationship, followed from a branch record that
    # DOES appear in an English-name search (e.g. "MUFG Bank Ltd, Jakarta
    # Branch" -> head-office -> 株式会社三菱UFJ銀行). All three of Mizuho's
    # branch records resolve to the same head office, cross-confirming it.
    "MUFG BANK LTD": {
        "lei": "C3GTMMZIHMY46P4OIX74",
        "legal_name": "MUFG Bank, Ltd.",
        "category": "GENERAL",
        "note": "Registered legal name is Japanese (株式会社三菱UFJ銀行); "
                "'MUFG Bank, Ltd.' is its GLEIF ALTERNATIVE_LANGUAGE_LEGAL_NAME. "
                "Found via the head-office relationship of the Jakarta "
                "Branch record (254900EV5JZKVXIBIB09), which the schedule's "
                "own branch-suffixed spellings correspond to.",
        "source": f"{GLEIF}/C3GTMMZIHMY46P4OIX74",
        "retrieved_at": RETRIEVED_AT,
    },
    "MIZUHO BANK LTD": {
        "lei": "RB0PEZSDGCO3JS6CEU02",
        "legal_name": "Mizuho Bank, Ltd.",
        "category": "GENERAL",
        "note": "Registered legal name is Japanese (株式会社みずほ銀行); "
                "'Mizuho Bank, Ltd.' is its GLEIF ALTERNATIVE_LANGUAGE_LEGAL_NAME. "
                "GLEIF's three 'MIZUHO BANK, LTD.' exact-name matches are "
                "all BRANCH-category records; all three resolve to this "
                "same head office via the head-office relationship, "
                "cross-confirming it.",
        "source": f"{GLEIF}/RB0PEZSDGCO3JS6CEU02",
        "retrieved_at": RETRIEVED_AT,
    },
    # BMO Bank, National Association and Citizens Bank, National
    # Association both resolve to exactly one ACTIVE exact match — but
    # only when queried with the fully expanded canonical form ("BMO Bank
    # National Association" / "Citizens Bank National Association"). The
    # raw schedule abbreviations ("BMO Bank N.A." / "Citizens Bank, N.A.")
    # don't reach the right record in GLEIF's own name index. Pinned here
    # rather than re-querying with a second, expanded string at runtime.
    "BMO BANK NATIONAL ASSOCIATION": {
        "lei": "3Y4U8VZURTYWI1W2K376",
        "legal_name": "BMO Bank National Association",
        "category": "GENERAL",
        "note": "Sole ACTIVE match when queried as 'BMO Bank National "
                "Association'; GLEIF's index does not surface it from the "
                "filed abbreviation 'BMO Bank N.A.'.",
        "source": f"{GLEIF}/3Y4U8VZURTYWI1W2K376",
        "retrieved_at": RETRIEVED_AT,
    },
    "CITIZENS BANK NATIONAL ASSOCIATION": {
        "lei": "DRMSV1Q0EKMEXLAU1P80",
        "legal_name": "Citizens Bank, National Association",
        "category": "GENERAL",
        "note": "Sole ACTIVE match (US-RI) when queried as 'Citizens Bank "
                "National Association'; an inactive duplicate under the "
                "identical name (549300D1D2WPHU5URX88) is excluded by "
                "status, and 'Citizens Business Bank' / 'Texas Citizens "
                "Bank' are different, unrelated entities.",
        "source": f"{GLEIF}/DRMSV1Q0EKMEXLAU1P80",
        "retrieved_at": RETRIEVED_AT,
    },
    # Two ACTIVE "Deutsche Bank Aktiengesellschaft" records. Disambiguated
    # via the Amsterdam Branch's head-office relationship, which points
    # to the record whose `registeredAs` (HRB 30000, Frankfurt) is Deutsche
    # Bank AG's well-known commercial register number.
    "DEUTSCHE BANK AG": {
        "lei": "7LTWFZYICNSX8D621K86",
        "legal_name": "Deutsche Bank Aktiengesellschaft",
        "category": "GENERAL",
        "note": "Confirmed via the head-office relationship of Deutsche "
                "Bank AG, Amsterdam Branch (724500G414AWQVQ8WV64), and by "
                "registeredAs 'HRB 30000' — Deutsche Bank AG's Frankfurt "
                "commercial register number. The other exact-name match "
                "(529900IH9V4I3VHQVO92) registers as '310 327 481'.",
        "source": f"{GLEIF}/7LTWFZYICNSX8D621K86",
        "retrieved_at": RETRIEVED_AT,
    },
}

#: Canonical keys that were searched exhaustively (legalName filter,
#: fulltext filter, name variants, abbreviation expansions, and — for the
#: Centerbridge-family names — a search on the parent fund family) and
#: returned NO real GLEIF LEI under any spelling. These are genuinely
#: unregistered, narrow investment vehicles, not an ambiguity a human
#: pick can resolve — and per Ruling T3-R1 (coordinator, after verifying
#: the GLEIF searches independently), that makes them members, not a
#: manual_review row: a real institution named in a real filed credit
#: agreement gets a member row with lei=None and a no_lei_reason, never
#: dropped and never given a SYN- synthetic identifier (that format is
#: reserved for INVENTED entities per CLAUDE.md, and these are real).
#: Padding them with an invented LEI, or silently promoting one to a
#: lookalike record (GLEIF has a "CB NC CO-INVEST, L.P." that shares the
#: "CB NC" prefix but omits "Centerbridge Special Credit Partners IV"
#: entirely) would both be the guessing CLAUDE.md forbids.
NO_LEI_FOUND = {
    "ASILIA CREDIT FUND LP",
    "CB SA FUND LP",
    "CENTERBRIDGE CREDIT CS LP",
    "CB NC CENTERBRIDGE SPECIAL CREDIT PARTNERS IV I CO INVEST LP",
    "TCW RESCUE FINANCING FUND II LP",
}

# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def _load_raw_names() -> list[str]:
    data = json.loads(SCHEDULES.read_text())
    names: set[str] = set()
    for agreement in data["agreements"]:
        for row in agreement["rows"]:
            names.add(row["lender_raw"])
    return sorted(names)


def _gleif_candidates(query: str) -> list[dict]:
    # page[size]=20, not 10: Bank of America's real entity-level record
    # (B4TYDEB6GKMZO031MB27) did not rank inside GLEIF's top 10 for the
    # exact query text that WAS used at first ("Bank of America, N.A.") --
    # only for a slightly different expansion. Ten was too narrow a window
    # to trust; twenty is cheap and catches more of this class.
    url = (f"{GLEIF}?filter%5Bentity.legalName%5D={quote(query, safe='')}"
           f"&page%5Bsize%5D=20")
    payload = get_json(url)
    out = []
    for rec in payload.get("data", []):
        a = rec["attributes"]
        e = a["entity"]
        out.append({
            "lei": a["lei"],
            "legal_name": e["legalName"]["name"],
            "jurisdiction": e.get("jurisdiction"),
            "status": e.get("status"),
            # entity.category discriminates the chartered institution
            # (GENERAL) from one of its own branch registrations (BRANCH),
            # which headquartersAddress cannot do -- every branch carries
            # its parent's HQ address by definition, so testing against
            # that field returns "correct" for the entity AND every branch
            # it has. See the Bank of America / Citibank fix for why this
            # matters: both were bound to a Jakarta branch registration
            # before this field was checked.
            "category": e.get("category"),
        })
    return out


def resolve_lei(canon_key: str, query_name: str) -> tuple[dict | None, list[dict]]:
    """Returns (chosen_record_or_None, all_ACTIVE_exact_normalised_matches).

    A candidate counts as a match only if it is ACTIVE and its own legal
    name normalises to the SAME canonical key as the query — a fuzzy top
    score is not good enough (Wells Fargo's top-scored FDIC search result
    for "Wells Fargo Bank" is a different, smaller Wells Fargo entity
    entirely). Exactly one such match resolves automatically; zero or many
    fall through to MANUAL_LEI / manual_review.

    BRANCH-category candidates are excluded from that automatic count
    entirely -- never a candidate for auto-resolution, not even as the
    sole survivor. Bank of America and Citibank were both bound to a
    Jakarta branch registration by the ORIGINAL version of this check,
    which accepted "exactly one ACTIVE exact-name match" with no regard
    for whether that match was the chartered entity or one of its own
    branches (headquartersAddress reads Charlotte/Sioux Falls on the
    branch record too -- every branch carries its parent's HQ address by
    definition, so that field can't discriminate). A canon_key whose only
    ACTIVE exact match is a BRANCH now falls through to manual_review /
    MANUAL_LEI instead of resolving silently.
    """
    if canon_key in MANUAL_LEI:
        m = MANUAL_LEI[canon_key]
        return {"lei": m["lei"], "legal_name": m["legal_name"],
                "category": m.get("category")}, []

    if canon_key in NO_LEI_FOUND:
        return None, []

    candidates = _gleif_candidates(query_name)
    exact = [c for c in candidates
             if c["status"] == "ACTIVE"
             and canonical_key(c["legal_name"]) == canon_key
             and c.get("category") != "BRANCH"]
    if len(exact) == 1:
        return exact[0], exact
    return None, exact


def _fdic_candidates(query: str) -> list[dict]:
    url = (f"{FDIC}/institutions?search=NAME:{quote(chr(34) + query + chr(34), safe=chr(34))}"
           f"&fields=NAME,CERT,FED_RSSD,ACTIVE&limit=10")
    payload = get_json(url)
    out = []
    for rec in payload.get("data", []):
        d = rec["data"]
        out.append({"name": d["NAME"], "cert": d.get("CERT"),
                     "rssd": d.get("FED_RSSD"), "active": d.get("ACTIVE")})
    return out


def resolve_rssd(canon_key: str, query_name: str) -> str | None:
    """Best-effort FDIC RSSD lookup. Absence is a legitimate outcome — funds,
    insurers and foreign banks operating through uninsured US branches are
    correctly missing from FDIC BankFind, which covers FDIC-insured
    institutions only. RSSD stays null for those; it is never invented."""
    candidates = _fdic_candidates(query_name)
    exact = [c for c in candidates
             if c["active"] == 1 and canonical_key(c["name"]) == canon_key]
    if len(exact) == 1:
        return str(exact[0]["rssd"])
    return None


CAPITAL_FIELDS = {
    "RBCT1J": "tier1_capital",
    "ASSET": "total_assets",
    "EQ": "total_equity",
}


def fetch_call_report(rssd: str, cert: int) -> dict | None:
    fields = ",".join(["REPDTE", *CAPITAL_FIELDS])
    payload = get_json(
        f"{FDIC}/financials?filters=CERT:{cert}&fields={fields}"
        f"&sort_by=REPDTE&sort_order=DESC&limit=1")
    rows = [r["data"] for r in payload.get("data", [])]
    if not rows:
        return None
    row = rows[0]
    out = {"rssd": rssd, "report_date": row.get("REPDTE")}
    for field, key in CAPITAL_FIELDS.items():
        out[key] = row.get(field)
    return out


def _cert_for(query: str, canon_key: str) -> int | None:
    for c in _fdic_candidates(query):
        if c["active"] == 1 and canonical_key(c["name"]) == canon_key:
            return c["cert"]
    return None


def member_id(lei: str | None, legal_name: str) -> tuple[str, str]:
    """Content-keyed member id. LEI-derived when an LEI exists; falls back
    to the normalised legal name when it doesn't (Ruling T3-R1 — a real
    filed entity with no discoverable real GLEIF LEI is still a member,
    never a SYN- synthetic identifier). Returns (member_id, id_basis) so
    a consumer never has to assume every id is LEI-derived — `id_basis`
    is `"lei"` or `"legal_name"`."""
    if lei is not None:
        digest = hashlib.sha256(lei.encode()).hexdigest()[:8]
        return f"SYNM-{digest}", "lei"
    digest = hashlib.sha256(("name:" + canonical_key(legal_name)).encode()).hexdigest()[:8]
    return f"SYNM-{digest}", "legal_name"


def main() -> int:
    print("Wave 18 Task 3 — resolving syndicate lenders to real LEI/RSSD\n")

    raw_names = _load_raw_names()
    groups: dict[str, list[str]] = {}
    manual_review: list[dict] = [{
        "lender_raw": CORRUPT_RAW,
        "reason": CORRUPT_REASON,
    }]

    for raw in raw_names:
        if raw == CORRUPT_RAW:
            continue
        key = canonical_key(raw)
        groups.setdefault(key, []).append(raw)

    print(f"  {len(raw_names)} raw lender strings -> {len(groups)} institutions "
          f"(+ 1 routed to manual_review as corrupt)\n")

    members: list[dict] = []
    call_reports: list[dict] = []

    for key in sorted(groups):
        raws = groups[key]
        # Query with the longest/most complete raw spelling in the group —
        # best odds of an exact GLEIF/FDIC name match.
        query_name = max(raws, key=len)

        lei_rec, exact_matches = resolve_lei(key, query_name)

        if lei_rec is None and key in NO_LEI_FOUND:
            # Ruling T3-R1: a real, filed institution with no discoverable
            # real GLEIF LEI is a MEMBER with lei=None — never dropped,
            # never given a synthetic identifier. "Legal name exactly as
            # filed" only means something for a single spelling, so this
            # assumes (and asserts) NO_LEI_FOUND groups are never merged.
            assert len(raws) == 1, (
                f"{key}: NO_LEI_FOUND group has {len(raws)} raw spellings — "
                f"'legal name exactly as filed' is ambiguous for a merged "
                f"group and needs a human decision, not this assertion.")
            legal_name = raws[0]
            no_lei_reason = (
                f"No real GLEIF LEI found for {legal_name!r} under any "
                f"spelling tried (legalName filter, fulltext search, "
                f"abbreviation expansions, parent-fund-family search). "
                f"Not an ambiguity — a genuinely unregistered vehicle.")
            mid, basis = member_id(None, legal_name)
            members.append({
                "member_id": mid,
                "id_basis": basis,
                "legal_name": legal_name,
                "lei": None,
                "no_lei_reason": no_lei_reason,
                "gleif_category": None,
                "rssd": None,
                "raw_names": raws,
                "provenance": "public",
                "source": f"GLEIF LEI records ({GLEIF}) — searched, no match found",
                "retrieved_at": RETRIEVED_AT,
            })
            print(f"  {legal_name:<55} lei=None (no real LEI found)  rssd=None")
            continue

        if lei_rec is None:
            # Genuinely ambiguous (0 or >1 ACTIVE exact matches) and NOT a
            # known no-LEI fund: needs a MANUAL_LEI entry, not a lei=None
            # member. "Searched and found nothing" (NO_LEI_FOUND, above) and
            # "found more than one and nobody has picked yet" (here) are
            # different findings and stay on different paths.
            reason = (f"GLEIF returned {len(exact_matches)} ACTIVE exact "
                      f"name matches for {query_name!r}; need exactly 1.")
            # One manual_review row per raw string (not per group) — every
            # entry's "lender_raw" is a single string, same shape as the
            # corrupt-string entry, so a consumer never has to branch on type.
            for raw in raws:
                manual_review.append({
                    "lender_raw": raw,
                    "canonical_key": key,
                    "reason": reason,
                    "candidates": exact_matches,
                })
            print(f"  MANUAL REVIEW  {key}  ({len(exact_matches)} ACTIVE matches, "
                  f"{len(raws)} raw string(s))")
            continue

        lei = lei_rec["lei"]
        legal_name = lei_rec["legal_name"]
        mid, basis = member_id(lei, legal_name)

        # RSSD is looked up under the OFFICIAL legal name (e.g. "Manufacturers
        # and Traders Trust Company"), not the filed abbreviation — FDIC's own
        # name index is exact-name sensitive the same way GLEIF's is.
        rssd = resolve_rssd(key, legal_name)
        source = f"GLEIF LEI records ({GLEIF}); FDIC BankFind ({FDIC})" if rssd \
            else f"GLEIF LEI records ({GLEIF}); no FDIC BankFind match (non-FDIC-insured or non-bank)"

        members.append({
            "member_id": mid,
            "id_basis": basis,
            "legal_name": legal_name,
            "lei": lei,
            # Never trust the field this project already tripped over once
            # this task (headquartersAddress can't tell an entity from its
            # own branch). category comes straight from the GLEIF record
            # chosen -- BRANCH is impossible to reach here (resolve_lei()
            # excludes it from automatic matches, and every MANUAL_LEI
            # entry carries its own hand-verified "category").
            "gleif_category": lei_rec.get("category"),
            "rssd": rssd,
            "raw_names": raws,
            "provenance": "public",
            "source": source,
            "retrieved_at": RETRIEVED_AT,
        })

        if rssd:
            cert = _cert_for(legal_name, key)
            if cert is not None:
                cr = fetch_call_report(rssd, cert)
                if cr:
                    call_reports.append(cr)

        tag = f"rssd={rssd}" if rssd else "rssd=None (no FDIC match)"
        print(f"  {legal_name:<55} lei={lei}  {tag}")

    with_lei = [m for m in members if m["lei"] is not None]
    with_rssd = [m for m in members if m["rssd"] is not None]
    print(f"\n  resolved: {len(members)} institutions "
          f"({len(with_lei)} with a real LEI, "
          f"{len(members) - len(with_lei)} with lei=None per Ruling T3-R1)")
    print(f"  {len(with_rssd)} of those carry an FDIC RSSD "
          f"(the rest: foreign bank branches or non-bank entities)")
    print(f"  call reports fetched: {len(call_reports)}")

    if len(manual_review) > 1:
        print(f"\n  {'=' * 70}")
        print(f"  MANUAL REVIEW — {len(manual_review) - 1} name(s) beyond the "
              f"known corrupt string could not be auto-resolved.")
        print(f"  Add a MANUAL_LEI entry (verified against gleif.org, dated) "
              f"before this task is done.")
        for entry in manual_review[1:]:
            print(f"    {entry['canonical_key']}: {entry['reason']}")
        print(f"  {'=' * 70}\n")

    out = {
        "generated_for": "wave18 · syndicated-lending-co-lender · Task 3",
        "method": "group filed lender_raw strings by canonical_key(), resolve "
                  "each group to one real GLEIF LEI (exact ACTIVE name match, "
                  "or hand-verified MANUAL_LEI), then FDIC BankFind for RSSD "
                  "and latest Call Report figures",
        "provenance": "public",
        "sources": {
            "lei": GLEIF,
            "rssd_and_call_report": f"{FDIC}/institutions, {FDIC}/financials",
        },
        "retrieved_at": RETRIEVED_AT,
        "members": members,
        "call_reports": call_reports,
        "manual_review": manual_review,
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"  written: {OUT.relative_to(REPO_ROOT)}")

    if len(manual_review) > 1:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
