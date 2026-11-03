#!/usr/bin/env python3
"""Pure Form 4 helpers — no network, no stores.

Form 4 is the spine of the Wave 10 person layer because it is the only source
in §C that is STRUCTURED: `rptOwnerCik`, `isDirector`, `isOfficer` and
`officerTitle` are typed fields, not prose. It also hands us §C's "hard join"
for free, since the reporting owner's CIK is a real, stable person identifier.

`raw_form4_url` exists because of a defect found on 2026-08-18. EDGAR's
`primaryDocument` for a Form 4 is `xslF345X06/ownership.xml` — the XSL-RENDERED
HTML view. Requesting it returns HTTP 200 and a complete HTML document, so it
fails as XML rather than as a fetch. Same family as the Wave 9 phantom
borrower: a constructed URL cannot fail loudly.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

#: Suffixes that mark a reporting owner as a legal entity rather than a person.
#: 10% owners are frequently holding companies; they must never become Person
#: nodes. Matched on the trailing token so "Wood William David III" stays natural.
_ENTITY_SUFFIXES = {
    "llc", "l.l.c.", "inc", "inc.", "corp", "corp.", "corporation", "lp", "l.p.",
    "llp", "plc", "ltd", "ltd.", "limited", "trust", "holdings", "partners",
    "partnership", "fund", "capital", "group", "company", "co", "co.", "nv",
    "n.v.", "sa", "s.a.", "ag", "gmbh", "bancorp", "associates", "ventures",
}

_TRUE = {"1", "true", "TRUE", "True"}

#: EDGAR appends the reporting owner's state of incorporation to a corporate
#: filer's name as a trailing `/XX/` token (e.g. "CHARTER COMMUNICATIONS,
#: INC. /MO/"). Stripped before tokenizing so it cannot mask the real
#: trailing token or be mistaken for part of the name.
#:
#: PUBLIC and exported: generators/fetch_13f.py::_norm_issuer needs the exact
#: same stripping (§8 known-issues — "AMPHENOL CORP /DE/" was normalising to
#: "amphenol de" and mis-banding ~1,850 rows as weak instead of strong). The
#: owner_kind fix landed this regex privately in this module; that was wrong
#: — a second consumer needing the identical rule is a signal the rule
#: belongs to neither caller alone. Import from here rather than copying.
STATE_SUFFIX = re.compile(r"\s*/[A-Za-z]{2}/\s*\Z")


@dataclass(frozen=True)
class ReportingOwner:
    cik: str
    name: str
    is_director: bool
    is_officer: bool
    is_ten_percent_owner: bool
    officer_title: str | None


def raw_form4_url(cik: int, accession: str, primary_document: str) -> str:
    """URL of the RAW Form 4 XML, not EDGAR's rendered HTML view."""
    document = primary_document.split("/")[-1]
    folder = accession.replace("-", "")
    return (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            f"{folder}/{document}")


def select_form4_filings(recent: dict, lookback: int) -> list[tuple[str, str, str]]:
    """The `lookback` most recent Form 4 filings from a submissions index."""
    rows = zip(recent["form"], recent["accessionNumber"],
               recent["filingDate"], recent["primaryDocument"])
    return [(a, d, p) for f, a, d, p in rows if f == "4"][:lookback]


def _text(node, tag: str) -> str | None:
    el = node.find(f".//{tag}")
    return el.text.strip() if el is not None and el.text else None


def parse_form4(xml_text: str) -> list[ReportingOwner]:
    """Every reporting owner declared on one Form 4."""
    cleaned = re.sub(r"^\s*<\?xml[^>]*\?>", "", xml_text).strip()
    root = ET.fromstring(cleaned)

    owners: list[ReportingOwner] = []
    for node in root.findall(".//reportingOwner"):
        cik = _text(node, "rptOwnerCik")
        name = _text(node, "rptOwnerName")
        if not cik or not name:
            continue
        rel = node.find(".//reportingOwnerRelationship")
        flag = (lambda t: (_text(rel, t) in _TRUE) if rel is not None else False)
        owners.append(ReportingOwner(
            cik=f"{int(cik):010d}",
            name=name,
            is_director=flag("isDirector"),
            is_officer=flag("isOfficer"),
            is_ten_percent_owner=flag("isTenPercentOwner"),
            officer_title=(_text(rel, "officerTitle") if rel is not None else None),
        ))
    return owners


def owner_kind(name: str) -> str:
    """`natural` or `entity`, from any token of the filed name.

    Checks every token, not just the trailing one: EDGAR's `/XX/` state
    marker or a trailing personal suffix ("... Trust I") can otherwise sit
    after the real entity marker and hide it — as it did for "CHARTER
    COMMUNICATIONS, INC. /MO/" (trailing token was "/MO/") and "ESS Holdings
    Business Trust I" (trailing token was "I"). The state marker is stripped
    first so it is never mistaken for a name token at all.
    """
    stripped = STATE_SUFFIX.sub("", name)
    tokens = re.sub(r"[,]", " ", stripped).split()
    if not tokens:
        return "natural"
    return ("entity" if any(t.lower() in _ENTITY_SUFFIXES for t in tokens)
            else "natural")
