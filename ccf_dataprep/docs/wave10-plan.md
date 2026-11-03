# Wave 10 — `client-360-coverage-graph` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load the client-360 coverage graph — a public person layer from four SEC sources and a wholly synthetic bank-side coverage and interaction graph — into Postgres and Fluree, with every §F condition query-verifiable.

**Architecture:** Form 4 is the spine: structured XML giving a real SEC CIK per person, from which DEF 14A, 8-K Item 5.02 and 13F act as bounded enrichment passes searching for *known* names rather than discovering new ones. Postgres owns every attribute; Fluree owns every edge and carries identity plus a display label only. The bank side — bankers, coverage, ~2,000 interactions, scoring weights — is generated and labelled `synthetic — internal`.

**Tech Stack:** Python 3.12, `uv`, `psycopg` 3, `requests`, stdlib `xml.etree.ElementTree`, `csv`, `zipfile`. Fluree 4.1.4 over SPARQL. **No pytest** — see Global Constraints.

**Spec:** `docs/wave10-design.md`

## Global Constraints

Every task's requirements implicitly include this section.

- **No pytest in this repo.** Tests are standalone executables: `#!/usr/bin/env python3`, a `CASES` list, a `main() -> int` printing `  [ok  ] label` / `  [FAIL] label`, and `sys.exit(main())`. Run as `uv run validators/test_x.py`. Pattern: `validators/test_binding_drift.py`.
- **Provenance is per element**, one of exactly `public`, `synthetic — internal`, `synthetic — engineered`. Never omit it, never infer it at review time.
- **Single-writer discipline.** Fluree holds edges, node types, and a display label. Every attribute resolves from Postgres. Never duplicate an attribute across stores.
- **Instance URIs are `ex:{LocalName}`** where `EX = "http://example.org/fibo/"`. **Never construct a URI for a node that has not been loaded** — build edge targets from loaded nodes. This is the Wave 9 phantom-borrower defect.
- **Every script takes `--dry-run` and is idempotent.** Postgres upserts; Fluree writes are `INSERT DATA` of stable triples.
- **Fluree SPARQL requires an explicit `FROM <ledger>`** — omitting it returns HTTP 500. `ccf/fluree.py` guards this; use `fluree.query()` / `fluree.update()`.
- **Fluree has no OWL inference.** Type every node explicitly for every role queried against.
- **No new FIBO bindings.** All required terms were bound in Wave 8. Six `ex:` extensions are minted: `ex:coversClient`, `ex:participatedIn`, `ex:relatedToDeal`, `ex:Banker`, `ex:Interaction`, `ex:Deal`.
- **`person_key` format:** zero-padded 10-digit CIK for real filers; `syn-p-<6 hex>` for minted. Visibly distinct, per the settled synthetic-identifier rule.
- **Form 4 lookback:** starts at 40 filings, doubles to a **hard cap of 160**, until ≥ 8 natural persons. Still short at 160 → **record a shortfall, do not pad**.
- **Real names load as filed** (user decision). This is scoped to DEF 14A and Form 4 only; CLAUDE.md rule 3 (PSC pseudonymization) and rule 2 (AML synthetic-only) are untouched.
- **Schema is `ccf_v2`**, ledger is `fibo-v2`. Never write to v1.
- **Fetched payloads are gitignored**; `sources/**/manifest.json` and `sources/screening/*.json` are tracked.

---

## File Structure

| File | Responsibility |
|---|---|
| `generators/form4.py` | **Pure.** Raw-XML URL derivation, filing selection, Form 4 parsing, natural-vs-entity classification |
| `generators/persons.py` | **Pure.** `person_key` minting, name parsing and normalization, variant detection, match scoring and banding |
| `generators/fetch_form4.py` | Network driver: fetch Form 4 XML for all 50 anchors, emit a filing index |
| `generators/extract_persons.py` | Build the person roster from fetched Form 4s |
| `generators/fetch_def14a.py` | Fetch proxies, bounded search for renderings of known names |
| `generators/fetch_8k502.py` | Select 8-Ks by `items`, extract appointment dates for known people |
| `generators/fetch_13f.py` | One quarterly dataset → institutional holders for the anchors |
| `generators/resolve_persons.py` | Build `person_crosswalk`; surface the natural false-positive pair |
| `generators/generate_coverage.py` | The whole bank side: bankers, coverage, interactions, weights |
| `loaders/load_postgres_wave10.py` | DDL + upserts for all nine new tables and two extended ones |
| `loaders/load_fluree_wave10.py` | Node types and six edge predicates |
| `validators/test_form4.py` | Pure tests for `form4.py` |
| `validators/test_persons.py` | Pure tests for `persons.py` |
| `validators/traversal.py` | The depth-2 truncation proof |

---

### Task 1: Form 4 pure functions — URL derivation, selection, parsing, owner kind

**Files:**
- Create: `generators/form4.py`
- Test: `validators/test_form4.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `raw_form4_url(cik: int, accession: str, primary_document: str) -> str`
  - `select_form4_filings(recent: dict, lookback: int) -> list[tuple[str, str, str]]` — returns `(accession, filing_date, primary_document)`
  - `@dataclass ReportingOwner` with fields `cik: str`, `name: str`, `is_director: bool`, `is_officer: bool`, `is_ten_percent_owner: bool`, `officer_title: str | None`
  - `parse_form4(xml_text: str) -> list[ReportingOwner]`
  - `owner_kind(name: str) -> str` — `"natural"` or `"entity"`

- [ ] **Step 1: Write the failing test**

Create `validators/test_form4.py`:

```python
#!/usr/bin/env python3
"""Pure tests for Form 4 URL derivation, selection, parsing and owner kind.

No network. The first case pins the 2026-08-18 probe defect: EDGAR's
`primaryDocument` names the XSL-RENDERED HTML view, which returns HTTP 200 and
a full HTML document. 120 filings failed silently and identically before anyone
looked at the bytes. A constructed URL cannot fail loudly.

    uv run validators/test_form4.py
"""

from __future__ import annotations

import sys

from generators.form4 import (ReportingOwner, owner_kind, parse_form4,
                              raw_form4_url, select_form4_filings)

FORM4_XML = """<?xml version="1.0"?>
<ownershipDocument>
  <issuer><issuerCik>0000078749</issuerCik></issuer>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0001277036</rptOwnerCik>
      <rptOwnerName>SRINIVASAN RAMESH</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>1</isDirector>
      <isOfficer>1</isOfficer>
      <officerTitle>President &amp; CEO</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0001266604</rptOwnerCik>
      <rptOwnerName>CCH II LLC</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isTenPercentOwner>true</isTenPercentOwner>
    </reportingOwnerRelationship>
  </reportingOwner>
</ownershipDocument>
"""

RECENT = {
    "form": ["4", "8-K", "4", "4", "DEF 14A"],
    "accessionNumber": ["a1", "a2", "a3", "a4", "a5"],
    "filingDate": ["2026-08-07", "2026-07-27", "2026-06-12", "2026-05-01", "2026-04-08"],
    "primaryDocument": ["xslF345X06/ownership.xml", "d1.htm",
                        "xslF345X06/ownership.xml", "ownership.xml", "d2.htm"],
}


def check_url() -> list[tuple[str, bool]]:
    got = raw_form4_url(78749, "0001193125-26-340549", "xslF345X06/ownership.xml")
    want = ("https://www.sec.gov/Archives/edgar/data/78749/"
            "000119312526340549/ownership.xml")
    bare = raw_form4_url(78749, "0001193125-26-340549", "ownership.xml")
    return [
        ("xsl-rendered prefix is stripped", got == want),
        ("dashes are removed from the accession", "000119312526340549" in got),
        ("an already-bare document is unchanged", bare == want),
    ]


def check_selection() -> list[tuple[str, bool]]:
    sel = select_form4_filings(RECENT, lookback=2)
    return [
        ("only form 4 is selected", all(a in {"a1", "a3", "a4"} for a, _, _ in sel)),
        ("lookback bounds the result", len(sel) == 2),
        ("most recent comes first", sel[0][0] == "a1"),
    ]


def check_parse() -> list[tuple[str, bool]]:
    owners = parse_form4(FORM4_XML)
    by_cik = {o.cik: o for o in owners}
    ceo = by_cik.get("0001277036")
    llc = by_cik.get("0001266604")
    return [
        ("both reporting owners are found", len(owners) == 2),
        ("cik is zero-padded to 10", ceo is not None and len(ceo.cik) == 10),
        ("isDirector 1 is truthy", ceo is not None and ceo.is_director),
        ("isOfficer 1 is truthy", ceo is not None and ceo.is_officer),
        ("officerTitle is carried, entities unescaped",
         ceo is not None and ceo.officer_title == "President & CEO"),
        ("isTenPercentOwner true is truthy",
         llc is not None and llc.is_ten_percent_owner),
        ("an owner with no title yields None",
         llc is not None and llc.officer_title is None),
    ]


def check_owner_kind() -> list[tuple[str, bool]]:
    natural = ["SRINIVASAN RAMESH", "Davison James E. Jr.", "alexander Richard R",
               "Jones Dana Sue", "Wood William David III"]
    entity = ["CCH II LLC", "Liberty Broadband Corp",
              "CHARTER COMMUNICATIONS HOLDINGS LLC", "GENESIS ENERGY LP"]
    return ([(f"natural: {n}", owner_kind(n) == "natural") for n in natural]
            + [(f"entity:  {n}", owner_kind(n) == "entity") for n in entity])


def main() -> int:
    cases = (check_url() + check_selection() + check_parse() + check_owner_kind())
    failures = sum(not ok for _, ok in cases)
    for label, ok in cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    print(f"\n  {len(cases) - failures}/{len(cases)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run validators/test_form4.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'generators.form4'`

- [ ] **Step 3: Write minimal implementation**

Create `generators/form4.py`:

```python
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
    """`natural` or `entity`, from the trailing token of the filed name."""
    tokens = re.sub(r"[,]", " ", name).split()
    if not tokens:
        return "natural"
    return "entity" if tokens[-1].lower() in _ENTITY_SUFFIXES else "natural"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run validators/test_form4.py`
Expected: PASS — `22/22 cases behave as specified`

- [ ] **Step 5: Commit**

```bash
git add generators/form4.py validators/test_form4.py
git commit -m "Wave 10: Form 4 pure helpers, with the rendered-view trap pinned by test"
```

---

### Task 2: Person identity pure functions — keys, names, variants, match bands

**Files:**
- Create: `generators/persons.py`
- Test: `validators/test_persons.py`

**Interfaces:**
- Consumes: `generators.form4.ReportingOwner`.
- Produces:
  - `person_key(cik: str | None, name: str) -> str` — 10-digit CIK, else `syn-p-<6 hex>` derived deterministically from the name
  - `parse_filed_name(name: str) -> dict` — keys `last`, `first`, `middle`, `suffix`
  - `normalize_name(name: str) -> str` — casefolded, punctuation-stripped, suffix-stripped, token-sorted
  - `render_display(parsed: dict) -> str` — `"First M Last Suffix"`
  - `match_score(a: str, b: str) -> float` — 0.0–1.0
  - `match_band(score: float, same_cik: bool | None) -> str` — `exact` | `strong` | `weak` | `false_positive`

- [ ] **Step 1: Write the failing test**

Create `validators/test_persons.py`:

```python
#!/usr/bin/env python3
"""Pure tests for person identity: keys, name parsing, scoring, banding.

Case group 4 pins the FALSE-POSITIVE PAIR found in the 2026-08-18 Form 4 probe:
`Davison James E` and `Davison James E. Jr.` file against the same issuer under
DISTINCT CIKs (1403411, 1403412). They are two different people whose names
fuzzy-match at near unity. CLAUDE.md rule 5 requires exactly one such pair, and
this one is REAL, so it is labelled `public` rather than engineered.

The banding function therefore must not resolve a near-unity score to a match
when the CIKs differ. A resolver that scores names and stops is the bug this
dataset exists to make visible.

    uv run validators/test_persons.py
"""

from __future__ import annotations

import sys

from generators.persons import (match_band, match_score, normalize_name,
                                parse_filed_name, person_key, render_display)


def check_keys() -> list[tuple[str, bool]]:
    real = person_key("0001277036", "SRINIVASAN RAMESH")
    minted_a = person_key(None, "Jane Q Public")
    minted_b = person_key(None, "Jane Q Public")
    minted_c = person_key(None, "John Q Public")
    return [
        ("a real CIK becomes the key verbatim", real == "0001277036"),
        ("a short CIK is zero-padded", person_key("78749", "X") == "0000078749"),
        ("a minted key carries the syn-p- prefix", minted_a.startswith("syn-p-")),
        ("minted keys are deterministic", minted_a == minted_b),
        ("different names mint different keys", minted_a != minted_c),
        ("a minted key is visibly not a CIK", not minted_a.isdigit()),
    ]


def check_name_parsing() -> list[tuple[str, bool]]:
    a = parse_filed_name("SRINIVASAN RAMESH")
    b = parse_filed_name("Davison James E. Jr.")
    c = parse_filed_name("Wood William David III")
    return [
        ("last name first is the filed order", a["last"] == "SRINIVASAN"),
        ("first name follows", a["first"] == "RAMESH"),
        ("a middle initial is captured", b["middle"] == "E."),
        ("a generational suffix is split off", b["suffix"] == "Jr."),
        ("suffix is not mistaken for a middle name", c["suffix"] == "III"),
        ("multi-token middle names survive", c["middle"] == "David"),
    ]


def check_normalization() -> list[tuple[str, bool]]:
    return [
        ("case is folded",
         normalize_name("SRINIVASAN RAMESH") == normalize_name("Srinivasan Ramesh")),
        ("filed order and display order agree",
         normalize_name("SRINIVASAN RAMESH") == normalize_name("Ramesh Srinivasan")),
        ("punctuation is dropped",
         normalize_name("Davison James E.") == normalize_name("Davison James E")),
        ("suffixes are stripped before comparison",
         normalize_name("Davison James E Jr.") == normalize_name("Davison James E")),
        ("distinct people still differ",
         normalize_name("Jones Dana Sue") != normalize_name("Jones Dana Lee")),
    ]


def check_false_positive_pair() -> list[tuple[str, bool]]:
    a, b = "Davison James E", "Davison James E. Jr."
    score = match_score(a, b)
    return [
        ("the real pair scores at or near unity", score >= 0.95),
        ("differing CIKs force a false_positive band",
         match_band(score, same_cik=False) == "false_positive"),
        ("the same CIK at the same score is exact",
         match_band(score, same_cik=True) == "exact"),
        ("an unknown CIK at a high score is only strong",
         match_band(score, same_cik=None) == "strong"),
        ("a middling score with no CIK is weak",
         match_band(0.72, same_cik=None) == "weak"),
        ("unrelated names do not band as strong",
         match_band(match_score("Jones Dana Sue", "MUTCH JOHN"), None) == "weak"),
    ]


def check_display() -> list[tuple[str, bool]]:
    d = render_display(parse_filed_name("SRINIVASAN RAMESH"))
    e = render_display(parse_filed_name("Davison James E. Jr."))
    return [
        ("display order is first-last", d == "RAMESH SRINIVASAN"),
        ("middle and suffix are preserved in display",
         e == "James E. Davison Jr."),
    ]


def main() -> int:
    cases = (check_keys() + check_name_parsing() + check_normalization()
             + check_false_positive_pair() + check_display())
    failures = sum(not ok for _, ok in cases)
    for label, ok in cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    print(f"\n  {len(cases) - failures}/{len(cases)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run validators/test_persons.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'generators.persons'`

- [ ] **Step 3: Write minimal implementation**

Create `generators/persons.py`:

```python
#!/usr/bin/env python3
"""Person identity: keys, filed-name parsing, normalization, match banding.

§C calls person identity "the hard join": DEF 14A gives names, Form 4 gives a
CIK per reporting person, and the CRM keys on an internal id. The crosswalk is
imperfect ON PURPOSE, per CLAUDE.md rule 5.

`match_band` is where that rule is enforced. A near-unity name score with
DIFFERING CIKs is not a match — it is a false positive, and the estate must say
so. The 2026-08-18 Form 4 probe found a real one at Genesis Energy: `Davison
James E` (CIK 1403411) and `Davison James E. Jr.` (CIK 1403412), two different
people. Because it is real, it is labelled `public`, not engineered.
"""

from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher

#: Generational and honorific suffixes, stripped before comparison so that
#: "Davison James E" and "Davison James E. Jr." collide as the rule intends.
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v", "md", "phd", "esq"}


def person_key(cik: str | None, name: str) -> str:
    """Zero-padded CIK where one exists, else a deterministic minted key."""
    if cik:
        return f"{int(cik):010d}"
    digest = hashlib.sha256(normalize_name(name).encode("utf-8")).hexdigest()
    return f"syn-p-{digest[:6]}"


def parse_filed_name(name: str) -> dict:
    """Split an EDGAR filed name, which is rendered `Last First Middle Suffix`."""
    tokens = [t for t in re.sub(r",", " ", name).split() if t]
    suffix = ""
    if tokens and tokens[-1].rstrip(".").lower() in _SUFFIXES:
        suffix = tokens.pop()
    last = tokens[0] if tokens else ""
    first = tokens[1] if len(tokens) > 1 else ""
    middle = " ".join(tokens[2:]) if len(tokens) > 2 else ""
    return {"last": last, "first": first, "middle": middle, "suffix": suffix}


def normalize_name(name: str) -> str:
    """Order-insensitive, case-insensitive, punctuation-free comparison form."""
    cleaned = re.sub(r"[^a-z0-9 ]", " ", name.lower())
    tokens = [t for t in cleaned.split() if t and t not in _SUFFIXES]
    return " ".join(sorted(tokens))


def render_display(parsed: dict) -> str:
    """`First Middle Last Suffix` — the human rendering, not the filed one."""
    parts = [parsed["first"], parsed["middle"], parsed["last"], parsed["suffix"]]
    return " ".join(p for p in parts if p)


def match_score(a: str, b: str) -> float:
    """Similarity of two names under `normalize_name`."""
    return SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio()


def match_band(score: float, same_cik: bool | None) -> str:
    """Band a candidate pair. CIK evidence outranks name similarity.

    A high score with DIFFERING CIKs is a false positive, not a match. This is
    the whole point of rule 5 — a resolver that scores names and stops is the
    failure the dataset exists to make visible.
    """
    if same_cik is False:
        return "false_positive" if score >= 0.90 else "weak"
    if same_cik is True:
        return "exact"
    return "strong" if score >= 0.90 else "weak"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run validators/test_persons.py`
Expected: PASS — `25/25 cases behave as specified`

- [ ] **Step 5: Commit**

```bash
git add generators/persons.py validators/test_persons.py
git commit -m "Wave 10: person identity helpers, with rule 5's false positive pinned"
```

---

### Task 3: Fetch Form 4 filings and build the person roster

**Files:**
- Create: `generators/fetch_form4.py`
- Create: `generators/extract_persons.py`
- Output: `sources/form4/**` (gitignored), `sources/form4/manifest.json`, `sources/screening/wave10_persons.json`

**Interfaces:**
- Consumes: `form4.raw_form4_url`, `form4.select_form4_filings`, `form4.parse_form4`, `form4.owner_kind`, `persons.person_key`, `persons.parse_filed_name`, `persons.render_display`.
- Produces: `sources/screening/wave10_persons.json` with shape
  ```json
  {"generated_at": "...", "lookback_used": {"<lei>": 40},
   "shortfalls": [{"lei": "...", "natural_persons": 6}],
   "persons": [{"person_key": "0001277036", "person_key_source": "sec_cik",
                "cik": "0001277036", "name_as_filed": "SRINIVASAN RAMESH",
                "display_name": "RAMESH SRINIVASAN", "owner_kind": "natural",
                "last": "SRINIVASAN", "first": "RAMESH", "middle": "", "suffix": "",
                "roles": [{"lei": "...", "role": "officer",
                           "officer_title": "President & CEO",
                           "first_seen": "2024-01-05", "last_seen": "2026-08-07"}]}]}
  ```

- [ ] **Step 1: Write the failing test**

Append to `validators/test_form4.py` a case group covering escalation, then wire it into `main()`:

```python
from generators.extract_persons import next_lookback


def check_escalation() -> list[tuple[str, bool]]:
    return [
        ("40 is the starting lookback", next_lookback(None, 0) == 40),
        ("a shortfall doubles the lookback", next_lookback(40, 6) == 80),
        ("doubling continues to 160", next_lookback(80, 7) == 160),
        ("160 is a hard cap — no further escalation",
         next_lookback(160, 6) is None),
        ("reaching 8 natural persons stops escalation",
         next_lookback(40, 8) is None),
        ("comfortably over the floor also stops",
         next_lookback(40, 21) is None),
    ]
```

Add `check_escalation()` to the `cases` tuple in `main()`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run validators/test_form4.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'generators.extract_persons'`

- [ ] **Step 3: Write minimal implementation**

Create `generators/extract_persons.py`:

```python
#!/usr/bin/env python3
"""Build the Wave 10 person roster from fetched Form 4 XML.

Escalation policy, per the design's global constraints: start at 40 filings and
double to a HARD CAP of 160 until an issuer yields >= 8 natural persons. An
issuer still short at 160 is RECORDED AS A SHORTFALL, never padded — hitting a
floor by invention is the "counted but not created" failure CLAUDE.md rejects.

    uv run generators/extract_persons.py --dry-run
    uv run generators/extract_persons.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone

from ccf.config import REPO_ROOT
from generators.form4 import owner_kind, parse_form4
from generators.persons import parse_filed_name, person_key, render_display

FORM4_ROOT = REPO_ROOT / "sources" / "form4"
SCREEN = REPO_ROOT / "sources" / "screening"
NATURAL_PERSON_FLOOR = 8
LOOKBACK_START = 40
LOOKBACK_CAP = 160


def next_lookback(current: int | None, natural_persons: int) -> int | None:
    """The lookback to try next, or None when escalation should stop."""
    if current is None:
        return LOOKBACK_START
    if natural_persons >= NATURAL_PERSON_FLOOR:
        return None
    doubled = current * 2
    return doubled if doubled <= LOOKBACK_CAP else None


def roster_for_issuer(lei: str, xml_paths: list) -> tuple[dict, int]:
    """Fold a set of Form 4 XML files into `{person_key: person}` for one issuer."""
    people: dict[str, dict] = {}
    seen: dict[tuple[str, str], list[str]] = defaultdict(list)

    for path, filing_date in xml_paths:
        try:
            owners = parse_form4(path.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            print(f"    [skip] {path.name}: {exc}")
            continue
        for owner in owners:
            key = person_key(owner.cik, owner.name)
            parsed = parse_filed_name(owner.name)
            person = people.setdefault(key, {
                "person_key": key,
                "person_key_source": "sec_cik",
                "cik": owner.cik,
                "name_as_filed": owner.name,
                "display_name": render_display(parsed),
                "owner_kind": owner_kind(owner.name),
                **{k: parsed[k] for k in ("last", "first", "middle", "suffix")},
                "roles": [],
            })
            for role, active in (("director", owner.is_director),
                                 ("officer", owner.is_officer),
                                 ("ten_percent_owner", owner.is_ten_percent_owner)):
                if not active:
                    continue
                seen[(key, role)].append(filing_date)
                existing = next((r for r in person["roles"]
                                 if r["lei"] == lei and r["role"] == role), None)
                if existing is None:
                    person["roles"].append({
                        "lei": lei, "role": role,
                        "officer_title": owner.officer_title,
                        "first_seen": filing_date, "last_seen": filing_date,
                    })
                else:
                    existing["first_seen"] = min(existing["first_seen"], filing_date)
                    existing["last_seen"] = max(existing["last_seen"], filing_date)
                    if owner.officer_title and not existing["officer_title"]:
                        existing["officer_title"] = owner.officer_title

    natural = sum(1 for p in people.values() if p["owner_kind"] == "natural")
    return people, natural


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    index = json.loads((SCREEN / "wave10_form4_index.json").read_text())
    all_people: dict[str, dict] = {}
    lookback_used: dict[str, int] = {}
    shortfalls: list[dict] = []

    for lei, entry in index["issuers"].items():
        paths = [(FORM4_ROOT / f["path"], f["filing_date"]) for f in entry["filings"]]
        lookback = None
        while True:
            step = next_lookback(lookback, 0 if lookback is None else natural)
            if step is None:
                break
            lookback = step
            people, natural = roster_for_issuer(lei, paths[:lookback])
            if natural >= NATURAL_PERSON_FLOOR or lookback >= LOOKBACK_CAP:
                break

        lookback_used[lei] = lookback
        if natural < NATURAL_PERSON_FLOOR:
            shortfalls.append({"lei": lei, "natural_persons": natural})
            print(f"  [short] {lei}: {natural} natural persons at lookback {lookback}")

        for key, person in people.items():
            merged = all_people.setdefault(key, person)
            if merged is not person:
                merged["roles"].extend(person["roles"])

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lookback_used": lookback_used,
        "shortfalls": shortfalls,
        "persons": sorted(all_people.values(), key=lambda p: p["person_key"]),
    }
    natural_total = sum(1 for p in payload["persons"] if p["owner_kind"] == "natural")
    print(f"\n  {len(payload['persons'])} reporting owners "
          f"({natural_total} natural, "
          f"{len(payload['persons']) - natural_total} entity) "
          f"across {len(lookback_used)} issuers · {len(shortfalls)} shortfalls")

    if args.dry_run:
        print("  [dry-run] nothing written")
        return 0
    SCREEN.mkdir(parents=True, exist_ok=True)
    (SCREEN / "wave10_persons.json").write_text(json.dumps(payload, indent=2))
    print(f"  wrote {SCREEN / 'wave10_persons.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run validators/test_form4.py`
Expected: PASS — `28/28 cases behave as specified`

- [ ] **Step 5: Write the fetch driver**

Create `generators/fetch_form4.py`:

```python
#!/usr/bin/env python3
"""Fetch Form 4 XML for all 50 anchors, at the escalating lookback.

~2,000 requests at the harness's 8 req/s, roughly five minutes. Every payload
goes through `ccf.fetch.fetch()` so retrieval date, URL and sha256 are recorded
without anyone remembering to.

**Fetch the RAW XML, never `primaryDocument` verbatim** — see `form4.raw_form4_url`.

    uv run generators/fetch_form4.py --dry-run
    uv run generators/fetch_form4.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.fetch import SourceManifest, fetch, get_json
from generators.extract_persons import LOOKBACK_CAP
from generators.form4 import raw_form4_url, select_form4_filings

SCREEN = REPO_ROOT / "sources" / "screening"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lookback", type=int, default=LOOKBACK_CAP,
                    help="filings to fetch per issuer; extract_persons walks "
                         "down from here, so fetch the cap once")
    args = ap.parse_args()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, cik FROM "{PG_SCHEMA_V2}".crosswalk '
                    "WHERE cik IS NOT NULL ORDER BY lei")
        anchors = cur.fetchall()
    print(f"  {len(anchors)} anchors with a CIK")

    manifest = SourceManifest(name="form4")
    index: dict = {"issuers": {}}

    for lei, cik in anchors:
        submissions = get_json(
            f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", is_sec=True)
        selected = select_form4_filings(submissions["filings"]["recent"], args.lookback)
        print(f"  {lei} cik={cik}: {len(selected)} Form 4 filings")

        filings = []
        for accession, filing_date, primary in selected:
            url = raw_form4_url(int(cik), accession, primary)
            filename = f"{int(cik):010d}/{accession}.xml"
            if not args.dry_run:
                fetch(url, manifest, filename, is_sec=True)
            filings.append({"accession": accession, "filing_date": filing_date,
                            "path": filename, "url": url})
        index["issuers"][lei] = {"cik": f"{int(cik):010d}", "filings": filings}

    index["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    index["source"] = "SEC EDGAR Form 4"
    index["provenance"] = "public"

    if args.dry_run:
        print("  [dry-run] nothing fetched or written")
        return 0
    SCREEN.mkdir(parents=True, exist_ok=True)
    (SCREEN / "wave10_form4_index.json").write_text(json.dumps(index, indent=2))
    print(f"  wrote {SCREEN / 'wave10_form4_index.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run the fetch, then the extract**

```bash
uv run generators/fetch_form4.py --dry-run     # confirm counts and URLs first
uv run generators/fetch_form4.py               # ~5 minutes
uv run generators/extract_persons.py
```

Expected: ~50 issuers, several hundred natural persons, shortfalls listed explicitly.
**If any issuer reports a shortfall, record it — do not raise the lookback past 160 and do not invent people.**

- [ ] **Step 7: Commit**

```bash
git add generators/fetch_form4.py generators/extract_persons.py \
        validators/test_form4.py sources/form4/manifest.json \
        sources/screening/wave10_form4_index.json sources/screening/wave10_persons.json
git commit -m "Wave 10: fetch Form 4 across the cast and build the person roster"
```

---

### Task 4: DEF 14A renderings and 8-K Item 5.02 appointment dates

**Files:**
- Create: `generators/fetch_def14a.py`
- Create: `generators/fetch_8k502.py`
- Output: `sources/screening/wave10_name_variants.json`, `sources/screening/wave10_appointments.json`

**Interfaces:**
- Consumes: `wave10_persons.json`, `persons.normalize_name`, `persons.match_score`.
- Produces:
  - `wave10_name_variants.json` — `[{"person_key", "variant_name", "source", "rendering", "provenance"}]`
  - `wave10_appointments.json` — `[{"person_key", "lei", "appointment_date", "accession", "item", "provenance"}]`

Both are **bounded searches for renderings of names already held**, not open-ended extraction. That inversion is §2 of the design and it is what makes yield measurable and partial failure survivable.

- [ ] **Step 1: Write the failing test**

Create `validators/test_renderings.py`:

```python
#!/usr/bin/env python3
"""Pure tests for bounded rendering search over DEF 14A / 8-K prose.

The point of the inversion: we are not asking "what officers exist in this
document?" — we hold the roster already. We are asking "how does this document
render RAMESH SRINIVASAN?". That has a known answer set, so a miss is visible.

    uv run validators/test_renderings.py
"""

from __future__ import annotations

import sys

from generators.fetch_def14a import find_renderings, strip_html

PROXY = """
<html><body>
<p>Our Board has nominated <b>Ramesh Srinivasan</b>, who has served as
President and Chief Executive Officer since 2017.</p>
<table><tr><td>Mr. R. Srinivasan</td><td>President &amp; CEO</td></tr>
<tr><td>Dana Sue Jones</td><td>Director</td></tr></table>
</body></html>
"""


def check_strip() -> list[tuple[str, bool]]:
    text = strip_html(PROXY)
    return [
        ("tags are removed", "<b>" not in text and "<td>" not in text),
        ("entities are unescaped", "&amp;" not in text and "&" in text),
        ("text survives", "Ramesh Srinivasan" in text),
        ("adjacent cells do not fuse into one token",
         "CEODana" not in text),
    ]


def check_find() -> list[tuple[str, bool]]:
    text = strip_html(PROXY)
    roster = [
        {"person_key": "0001277036", "last": "SRINIVASAN", "first": "RAMESH",
         "name_as_filed": "SRINIVASAN RAMESH"},
        {"person_key": "0001775010", "last": "Jones", "first": "Dana",
         "name_as_filed": "Jones Dana Sue"},
        {"person_key": "0000000001", "last": "Nobody", "first": "Absent",
         "name_as_filed": "Nobody Absent"},
    ]
    found = {r["person_key"]: r for r in find_renderings(text, roster, source="def14a")}
    return [
        ("a display-order rendering is found", "0001277036" in found),
        ("the variant is the DOCUMENT's rendering, not the filed one",
         found.get("0001277036", {}).get("variant_name") == "Ramesh Srinivasan"),
        ("a second person is found independently", "0001775010" in found),
        ("a person absent from the document is not invented",
         "0000000001" not in found),
        ("provenance is public", all(v["provenance"] == "public"
                                     for v in found.values())),
        ("source is carried", all(v["source"] == "def14a" for v in found.values())),
    ]


def main() -> int:
    cases = check_strip() + check_find()
    failures = sum(not ok for _, ok in cases)
    for label, ok in cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    print(f"\n  {len(cases) - failures}/{len(cases)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run validators/test_renderings.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'generators.fetch_def14a'`

- [ ] **Step 3: Write minimal implementation**

Create `generators/fetch_def14a.py`:

```python
#!/usr/bin/env python3
"""Fetch DEF 14A proxies and find how each renders names we already hold.

48 of 50 anchors file a proxy; the two that do not are MLPs, which hold no
annual meeting. They lose nothing — Form 4 already supplied their roster.

This is the ENRICHMENT pass, not the discovery pass. Yield is measured against
the known roster, so a shortfall costs variants rather than people.

    uv run generators/fetch_def14a.py --dry-run
    uv run generators/fetch_def14a.py
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.fetch import SourceManifest, fetch, get_json

SCREEN = REPO_ROOT / "sources" / "screening"
DEF14A_ROOT = REPO_ROOT / "sources" / "def14a"


def strip_html(raw: str) -> str:
    """Tags out, entities decoded, whitespace collapsed — cells stay separated."""
    without_scripts = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    spaced = re.sub(r"(?s)<[^>]+>", " ", without_scripts)
    return re.sub(r"\s+", " ", html.unescape(spaced)).strip()


def find_renderings(text: str, roster: list[dict], *, source: str) -> list[dict]:
    """For each roster member, the document's own rendering of their name.

    Bounded search: the answer set is the roster. A person the document does not
    mention yields nothing, and is never invented.
    """
    found: list[dict] = []
    for person in roster:
        last, first = person["last"], person["first"]
        if not last or not first:
            continue
        initial = re.escape(first[0])
        pattern = re.compile(
            rf"\b((?:{re.escape(first)}|{initial}\.?)"
            rf"(?:\s+[A-Z][a-zA-Z.'-]*)?\s+{re.escape(last)})\b",
            re.IGNORECASE)
        match = pattern.search(text)
        if not match:
            continue
        variant = re.sub(r"\s+", " ", match.group(1)).strip()
        if variant.lower() == person["name_as_filed"].lower():
            continue
        found.append({
            "person_key": person["person_key"],
            "variant_name": variant,
            "source": source,
            "rendering": "display_order",
            "provenance": "public",
        })
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    roster_doc = json.loads((SCREEN / "wave10_persons.json").read_text())
    by_lei: dict[str, list[dict]] = {}
    for person in roster_doc["persons"]:
        if person["owner_kind"] != "natural":
            continue
        for role in person["roles"]:
            by_lei.setdefault(role["lei"], []).append(person)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, cik FROM "{PG_SCHEMA_V2}".crosswalk '
                    "WHERE cik IS NOT NULL ORDER BY lei")
        anchors = cur.fetchall()

    manifest = SourceManifest(name="def14a")
    variants: list[dict] = []
    no_proxy: list[str] = []

    for lei, cik in anchors:
        submissions = get_json(
            f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", is_sec=True)
        recent = submissions["filings"]["recent"]
        rows = [(a, d, p) for f, a, d, p in zip(
            recent["form"], recent["accessionNumber"],
            recent["filingDate"], recent["primaryDocument"])
            if f.startswith("DEF 14A")]
        if not rows:
            no_proxy.append(lei)
            print(f"  [none ] {lei}: no DEF 14A (expected for an MLP)")
            continue

        accession, filing_date, primary = rows[0]
        url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
               f"{accession.replace('-', '')}/{primary}")
        filename = f"{int(cik):010d}/{accession}.htm"
        if args.dry_run:
            print(f"  [plan  ] {lei}: {url}")
            continue

        path = fetch(url, manifest, filename, is_sec=True)
        text = strip_html(path.read_text(encoding="utf-8", errors="replace"))
        roster = by_lei.get(lei, [])
        hits = find_renderings(text, roster, source="def14a")
        variants.extend(hits)
        print(f"  [ok    ] {lei}: {len(hits)} renderings from {len(roster)} roster")

    if args.dry_run:
        print("  [dry-run] nothing fetched or written")
        return 0

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "SEC EDGAR DEF 14A",
        "anchors_without_a_proxy": no_proxy,
        "variants": variants,
    }
    (SCREEN / "wave10_name_variants.json").write_text(json.dumps(payload, indent=2))
    print(f"\n  {len(variants)} renderings · {len(no_proxy)} anchors without a proxy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run validators/test_renderings.py`
Expected: PASS — `10/10 cases behave as specified`

- [ ] **Step 5: Write the 8-K Item 5.02 driver**

Create `generators/fetch_8k502.py`. Selection is free — the submissions index exposes an `items` field, so no document is parsed to decide relevance:

```python
#!/usr/bin/env python3
"""Appointment and departure dates from 8-K Item 5.02.

Selection costs nothing: the EDGAR submissions index carries an `items` field
per filing, so Item 5.02 is a string match on METADATA. Only matching filings
are fetched, and each is searched for surnames already on the roster.

    uv run generators/fetch_8k502.py --dry-run
    uv run generators/fetch_8k502.py
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

SCREEN = REPO_ROOT / "sources" / "screening"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-per-issuer", type=int, default=12)
    args = ap.parse_args()

    roster_doc = json.loads((SCREEN / "wave10_persons.json").read_text())
    by_lei: dict[str, list[dict]] = {}
    for person in roster_doc["persons"]:
        if person["owner_kind"] != "natural":
            continue
        for role in person["roles"]:
            by_lei.setdefault(role["lei"], []).append(person)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, cik FROM "{PG_SCHEMA_V2}".crosswalk '
                    "WHERE cik IS NOT NULL ORDER BY lei")
        anchors = cur.fetchall()

    manifest = SourceManifest(name="form8k502")
    appointments: list[dict] = []

    for lei, cik in anchors:
        submissions = get_json(
            f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", is_sec=True)
        recent = submissions["filings"]["recent"]
        items = recent.get("items", [""] * len(recent["form"]))
        rows = [(a, d, p) for f, a, d, p, it in zip(
            recent["form"], recent["accessionNumber"], recent["filingDate"],
            recent["primaryDocument"], items)
            if f == "8-K" and "5.02" in (it or "")][:args.max_per_issuer]
        print(f"  {lei}: {len(rows)} Item 5.02 filings")
        if args.dry_run:
            continue

        for accession, filing_date, primary in rows:
            url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                   f"{accession.replace('-', '')}/{primary}")
            path = fetch(url, manifest, f"{int(cik):010d}/{accession}.htm", is_sec=True)
            text = strip_html(path.read_text(encoding="utf-8", errors="replace"))
            for person in by_lei.get(lei, []):
                last = person["last"]
                if not last or not re.search(rf"\b{re.escape(last)}\b", text,
                                             re.IGNORECASE):
                    continue
                appointments.append({
                    "person_key": person["person_key"],
                    "lei": lei,
                    "appointment_date": filing_date,
                    "accession": accession,
                    "item": "5.02",
                    "provenance": "public",
                })

    if args.dry_run:
        print("  [dry-run] nothing fetched or written")
        return 0

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "SEC EDGAR 8-K Item 5.02",
        "appointments": appointments,
    }
    (SCREEN / "wave10_appointments.json").write_text(json.dumps(payload, indent=2))
    print(f"\n  {len(appointments)} appointment records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run both drivers**

```bash
uv run generators/fetch_def14a.py --dry-run && uv run generators/fetch_def14a.py
uv run generators/fetch_8k502.py --dry-run  && uv run generators/fetch_8k502.py
```

Expected: `anchors_without_a_proxy` contains **exactly the two MLPs** (`CrossAmerica Partners LP`, `GENESIS ENERGY LP`). Any other anchor appearing there is a regression — investigate before continuing.
**The variant count must reach at least 5** to satisfy §F. It should greatly exceed it; if it does not, that is a finding to record, not a number to force.

- [ ] **Step 7: Commit**

```bash
git add generators/fetch_def14a.py generators/fetch_8k502.py \
        validators/test_renderings.py sources/def14a/manifest.json \
        sources/form8k502/manifest.json \
        sources/screening/wave10_name_variants.json \
        sources/screening/wave10_appointments.json
git commit -m "Wave 10: bounded rendering search over proxies, and 8-K 5.02 dates"
```

---

### Task 5: Form 13F institutional holders

**Files:**
- Create: `generators/fetch_13f.py`
- Output: `sources/13f/**` (gitignored), `sources/screening/wave10_holders.json`

**Interfaces:**
- Consumes: `persons.match_score` (reused for issuer-name matching), `ccf.fetch.fetch`.
- Produces: `wave10_holders.json` — `[{"lei", "cusip", "manager_cik", "manager_name", "value_usd", "shares", "report_period", "issuer_match_band", "issuer_match_score", "provenance"}]`

13F is filed per **manager**, listing that manager's whole book, so finding holders of one issuer is an inverted-index problem. One quarterly structured dataset solves it; §C wants 13F as relationship context only, so a single quarter suffices.

- [ ] **Step 1: Write the implementation**

Create `generators/fetch_13f.py`:

```python
#!/usr/bin/env python3
"""Institutional holders of the anchors, from one quarterly 13F dataset.

The SEC's dataset naming CHANGED: the old `<YYYY>q<N>_form13f.zip` pattern 404s
for recent periods. Current form is a date range, e.g.
`01mar2026-31may2026_form13f.zip` (~99 MB).

Issuer matching is fuzzy — `NAMEOFISSUER` against our legal names — so every row
carries a band. §C asks for 13F as context only, so an imperfect match degrades
gracefully rather than corrupting a join.

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
from datetime import datetime, timezone

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.fetch import SourceManifest, fetch
from generators.persons import match_score

SCREEN = REPO_ROOT / "sources" / "screening"
BASE = "https://www.sec.gov/files/structureddata/data/form-13f-data-sets"
STRONG, WEAK = 0.92, 0.80


def _norm_issuer(name: str) -> str:
    drop = {"inc", "inc.", "corp", "corp.", "corporation", "co", "co.", "the",
            "lp", "l.p.", "llc", "plc", "ltd", "holdings", "group", "trust"}
    tokens = [t for t in "".join(
        c if c.isalnum() or c.isspace() else " " for c in name.lower()).split()
        if t not in drop]
    return " ".join(tokens)


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

    manifest = SourceManifest(name="13f")
    path = fetch(url, manifest, f"{args.period}_form13f.zip")

    holders: list[dict] = []
    with zipfile.ZipFile(path) as zf:
        names = {n.upper(): n for n in zf.namelist()}
        cover_name = next(n for u, n in names.items() if u.startswith("COVERPAGE"))
        info_name = next(n for u, n in names.items() if u.startswith("INFOTABLE"))

        managers: dict[str, dict] = {}
        with zf.open(cover_name) as fh:
            for row in csv.DictReader(io.TextIOWrapper(fh, "utf-8", errors="replace"),
                                      delimiter="\t"):
                managers[row["ACCESSION_NUMBER"]] = {
                    "manager_name": row.get("FILINGMANAGER_NAME", ""),
                    "report_period": row.get("PERIODOFREPORT", ""),
                }

        with zf.open(info_name) as fh:
            for row in csv.DictReader(io.TextIOWrapper(fh, "utf-8", errors="replace"),
                                      delimiter="\t"):
                issuer = _norm_issuer(row.get("NAMEOFISSUER", ""))
                if not issuer:
                    continue
                best_lei, best_score = None, 0.0
                for lei, _, normalized in anchors:
                    score = match_score(issuer, normalized)
                    if score > best_score:
                        best_lei, best_score = lei, score
                if best_score < WEAK:
                    continue
                meta = managers.get(row["ACCESSION_NUMBER"], {})
                holders.append({
                    "lei": best_lei,
                    "cusip": row.get("CUSIP", ""),
                    "manager_cik": row["ACCESSION_NUMBER"].split("-")[0],
                    "manager_name": meta.get("manager_name", ""),
                    "value_usd": row.get("VALUE", ""),
                    "shares": row.get("SSHPRNAMT", ""),
                    "report_period": meta.get("report_period", ""),
                    "issuer_match_score": round(best_score, 4),
                    "issuer_match_band": "strong" if best_score >= STRONG else "weak",
                    "provenance": "public",
                })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": f"SEC Form 13F data set {args.period}",
        "holders": holders,
    }
    (SCREEN / "wave10_holders.json").write_text(json.dumps(payload, indent=2))
    strong = sum(1 for h in holders if h["issuer_match_band"] == "strong")
    print(f"\n  {len(holders)} holdings · {strong} strong / {len(holders) - strong} weak")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it**

```bash
uv run generators/fetch_13f.py --dry-run
uv run generators/fetch_13f.py --period 01mar2026-31may2026
```

Expected: a non-trivial holder count with a mix of strong and weak bands.
**If the period 404s, list available periods first** — the naming convention has changed once already:

```bash
uv run python -c "
import re, requests
from ccf.fetch import sec_headers
r = requests.get('https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets', headers=sec_headers(), timeout=30)
print('\n'.join(sorted(set(re.findall(r'href=\"([^\"]*13[fF][^\"]*\.zip)\"', r.text)))[-6:]))"
```

- [ ] **Step 3: Commit**

```bash
git add generators/fetch_13f.py sources/13f/manifest.json \
        sources/screening/wave10_holders.json
git commit -m "Wave 10: institutional holders from one quarterly 13F data set"
```

---

### Task 6: Resolve person identity and build the crosswalk

**Files:**
- Create: `generators/resolve_persons.py`
- Output: `sources/screening/wave10_crosswalk.json`

**Interfaces:**
- Consumes: `wave10_persons.json`, `wave10_name_variants.json`, `persons.match_score`, `persons.match_band`, `persons.normalize_name`.
- Produces: `wave10_crosswalk.json` — `{"rows": [{"source_system", "source_id", "source_name", "person_key", "match_score", "match_band", "is_true_match", "provenance", "note"}], "false_positive_pairs": [...]}`

- [ ] **Step 1: Write the failing test**

Create `validators/test_resolve.py`:

```python
#!/usr/bin/env python3
"""Pure test for false-positive detection across the roster.

Rule 5 requires >= 1 pair of DIFFERENT people who fuzzy-match strongly. The
2026-08-18 Form 4 probe found a real one, so this is a detector for a condition
that already exists rather than a planter of one.

    uv run validators/test_resolve.py
"""

from __future__ import annotations

import sys

from generators.resolve_persons import find_false_positive_pairs

ROSTER = [
    {"person_key": "0001403411", "name_as_filed": "Davison James E",
     "owner_kind": "natural"},
    {"person_key": "0001403412", "name_as_filed": "Davison James E. Jr.",
     "owner_kind": "natural"},
    {"person_key": "0001277036", "name_as_filed": "SRINIVASAN RAMESH",
     "owner_kind": "natural"},
    {"person_key": "0001266604", "name_as_filed": "CCH II LLC",
     "owner_kind": "entity"},
]


def main() -> int:
    pairs = find_false_positive_pairs(ROSTER)
    keys = {tuple(sorted((p["person_key_a"], p["person_key_b"]))) for p in pairs}
    cases = [
        ("the real Davison pair is detected",
         ("0001403411", "0001403412") in keys),
        ("exactly one pair is found in this roster", len(pairs) == 1),
        ("the pair scores at or above the band threshold",
         all(p["match_score"] >= 0.90 for p in pairs)),
        ("it is banded false_positive, not a match",
         all(p["match_band"] == "false_positive" for p in pairs)),
        ("is_true_match is False", all(p["is_true_match"] is False for p in pairs)),
        ("provenance is public — the collision is real, not planted",
         all(p["provenance"] == "public" for p in pairs)),
        ("entities are excluded from person matching",
         all("0001266604" not in (p["person_key_a"], p["person_key_b"])
             for p in pairs)),
        ("a person does not match themselves",
         all(p["person_key_a"] != p["person_key_b"] for p in pairs)),
    ]
    failures = sum(not ok for _, ok in cases)
    for label, ok in cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    print(f"\n  {len(cases) - failures}/{len(cases)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run validators/test_resolve.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'generators.resolve_persons'`

- [ ] **Step 3: Write minimal implementation**

Create `generators/resolve_persons.py`:

```python
#!/usr/bin/env python3
"""Build `person_crosswalk` and surface the false-positive pair.

§C: "Person identity is the hard join." The crosswalk is synthetic and
imperfect ON PURPOSE — a demo where every person resolves cleanly teaches the
wrong lesson and makes the resolution logic untestable.

The false-positive pair is NOT planted. The 2026-08-18 probe found a real one:
`Davison James E` (CIK 1403411) and `Davison James E. Jr.` (CIK 1403412), both
filing against Genesis Energy, two different people. Provenance is therefore
`public`. A found collision proves the case occurs in the wild; a planted one
proves only that the resolver handles a case built for it.

    uv run generators/resolve_persons.py --dry-run
    uv run generators/resolve_persons.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from itertools import combinations

from ccf.config import REPO_ROOT
from generators.persons import match_band, match_score

SCREEN = REPO_ROOT / "sources" / "screening"
FALSE_POSITIVE_FLOOR = 0.90


def find_false_positive_pairs(roster: list[dict]) -> list[dict]:
    """Distinct natural persons whose names collide at or above the floor."""
    people = [p for p in roster if p.get("owner_kind") == "natural"]
    pairs: list[dict] = []
    for a, b in combinations(people, 2):
        if a["person_key"] == b["person_key"]:
            continue
        score = match_score(a["name_as_filed"], b["name_as_filed"])
        if score < FALSE_POSITIVE_FLOOR:
            continue
        pairs.append({
            "person_key_a": a["person_key"],
            "person_key_b": b["person_key"],
            "name_a": a["name_as_filed"],
            "name_b": b["name_as_filed"],
            "match_score": round(score, 4),
            "match_band": match_band(score, same_cik=False),
            "is_true_match": False,
            "provenance": "public",
            "note": "distinct SEC CIKs; names collide at or above the floor",
        })
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    roster = json.loads((SCREEN / "wave10_persons.json").read_text())["persons"]
    variants = json.loads(
        (SCREEN / "wave10_name_variants.json").read_text())["variants"]
    by_key = {p["person_key"]: p for p in roster}

    rows: list[dict] = []

    # Form 4 resolves exactly: the CIK IS the key.
    for person in roster:
        rows.append({
            "source_system": "form4",
            "source_id": person["cik"],
            "source_name": person["name_as_filed"],
            "person_key": person["person_key"],
            "match_score": 1.0,
            "match_band": "exact",
            "is_true_match": True,
            "provenance": "public",
            "note": "reporting owner CIK is the person key",
        })

    # DEF 14A resolves by name against a known roster — genuinely imperfect.
    for variant in variants:
        person = by_key.get(variant["person_key"])
        if person is None:
            continue
        score = match_score(variant["variant_name"], person["name_as_filed"])
        rows.append({
            "source_system": "def14a",
            "source_id": f"{variant['person_key']}:{variant['variant_name']}",
            "source_name": variant["variant_name"],
            "person_key": variant["person_key"],
            "match_score": round(score, 4),
            "match_band": match_band(score, same_cik=None),
            "is_true_match": True,
            "provenance": "synthetic — engineered",
            "note": "resolved by bounded name search, not by identifier",
        })

    pairs = find_false_positive_pairs(roster)
    for pair in pairs:
        rows.append({
            "source_system": "resolver",
            "source_id": pair["person_key_b"],
            "source_name": pair["name_b"],
            "person_key": pair["person_key_a"],
            "match_score": pair["match_score"],
            "match_band": "false_positive",
            "is_true_match": False,
            "provenance": "public",
            "note": pair["note"],
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows": rows,
        "false_positive_pairs": pairs,
    }
    print(f"  {len(rows)} crosswalk rows · {len(pairs)} false-positive pairs")
    for pair in pairs:
        print(f"    [fp] {pair['name_a']}  <->  {pair['name_b']}  "
              f"score={pair['match_score']}")

    if not pairs:
        print("\n  WARNING: rule 5 requires >= 1 false-positive pair and none was "
              "found. Do NOT plant one silently — record the shortfall and raise it.")

    if args.dry_run:
        print("  [dry-run] nothing written")
        return 0
    (SCREEN / "wave10_crosswalk.json").write_text(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run validators/test_resolve.py`
Expected: PASS — `8/8 cases behave as specified`

- [ ] **Step 5: Run against the real roster**

```bash
uv run generators/resolve_persons.py --dry-run
uv run generators/resolve_persons.py
```

Expected: at least one `[fp]` line, including the Davison pair. If none appears, **stop and report it** — do not plant a pair to satisfy the rule.

- [ ] **Step 6: Commit**

```bash
git add generators/resolve_persons.py validators/test_resolve.py \
        sources/screening/wave10_crosswalk.json
git commit -m "Wave 10: person crosswalk, and the real false-positive pair it finds"
```

---

### Task 7: Generate the bank side

**Files:**
- Create: `generators/generate_coverage.py`
- Output: `sources/screening/wave10_coverage.json`

**Interfaces:**
- Consumes: `wave10_persons.json`, existing `ccf_v2.principal` and `ccf_v2.deal`.
- Produces: `wave10_coverage.json` with keys `bankers`, `coverage_assignments`, `interactions`, `participants`, `scoring_weights`, `coverage_gaps`, `dense_anchor`.

Every element here is invented, because interaction history exists nowhere public. §C: the public-to-synthetic ratio **inverts** in this product.

**Two conditions counting cannot fake** — see design §5.1:
- interactions must be **recency-weighted**, so recent-quarter density materially exceeds oldest-quarter density
- one anchor must exceed **200 nodes at depth 2**, which requires deliberate concentration

- [ ] **Step 1: Write the failing test**

Create `validators/test_coverage_shape.py`:

```python
#!/usr/bin/env python3
"""Pure tests for the two bank-side conditions that counting cannot fake.

A flat 2,000 interactions satisfies §F's number and DEFEATS ITS PURPOSE:
relationship-strength scoring needs a real gradient to measure. And an even
spread across 50 anchors puts every client near 40 nodes, making §F's
`limit=200` truncation case unreachable.

    uv run validators/test_coverage_shape.py
"""

from __future__ import annotations

import sys

from generators.generate_coverage import (allocate_interactions,
                                          recency_weights)


def main() -> int:
    weights = recency_weights(quarters=8)
    alloc = allocate_interactions(total=2000, anchors=[f"LEI{i:02d}" for i in range(50)],
                                  dense_anchor="LEI00", dense_share=0.12)
    dense = alloc["LEI00"]
    others = [v for k, v in alloc.items() if k != "LEI00"]

    cases = [
        ("weights cover every quarter", len(weights) == 8),
        ("weights are normalised", abs(sum(weights) - 1.0) < 1e-9),
        ("the most recent quarter is heaviest", weights[0] == max(weights)),
        ("the oldest quarter is lightest", weights[-1] == min(weights)),
        ("recency is a real gradient, not a tilt",
         weights[0] >= 2.0 * weights[-1]),
        ("the allocation totals the target", sum(alloc.values()) == 2000),
        ("every anchor gets some interactions", all(v > 0 for v in alloc.values())),
        ("the dense anchor is deliberately concentrated",
         dense >= 3 * (sum(others) / len(others))),
        ("the dense anchor can exceed a 200-node depth-2 traversal",
         dense >= 200),
    ]
    failures = sum(not ok for _, ok in cases)
    for label, ok in cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    print(f"\n  {len(cases) - failures}/{len(cases)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run validators/test_coverage_shape.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'generators.generate_coverage'`

- [ ] **Step 3: Write minimal implementation**

Create `generators/generate_coverage.py`:

```python
#!/usr/bin/env python3
"""Generate the entire bank side of client-360. All `synthetic — internal`.

§C: interaction history exists nowhere public, so every element here is
invented. That is not a weakness in the demo — it is an accurate depiction of
the problem, and it is why no vendor can supply this half.

Two conditions are shaped rather than counted:

  recency weighting  — relationship strength decays with the interactions
                       beneath it (§E gives interaction records λ_c ~7 days),
                       so a FLAT distribution makes the score meaningless
  dense anchor       — §F wants >= 1 client whose depth-2 traversal exceeds
                       limit=200, and an even spread makes that unreachable

Determinism: seeded from a fixed constant so re-runs are byte-stable. No
`Math.random`-style drift between loads.

    uv run generators/generate_coverage.py --dry-run
    uv run generators/generate_coverage.py
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date, datetime, timedelta, timezone

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
SEED = 20261018
BANKER_COUNT = 40
INTERACTION_TOTAL = 2000
MONTHS = 24
DENSE_SHARE = 0.12
NEED_TO_KNOW_COUNT = 10
COVERAGE_GAP_COUNT = 3

ROLES = ["coverage", "product", "credit"]
SENIORITY = ["analyst", "associate", "vice_president", "director", "managing_director"]
CHANNELS = ["meeting", "call", "email"]
FIRST = ["Alex", "Priya", "Marcus", "Yuki", "Sofia", "Daniel", "Nadia", "Tomas",
         "Grace", "Omar", "Elena", "Kwame", "Ingrid", "Rafael", "Mei", "Jonas"]
LAST = ["Okafor", "Lindqvist", "Varga", "Rahman", "Castellanos", "Novak",
        "Adeyemi", "Fischer", "Moreau", "Tanaka", "Silva", "Haddad",
        "Kowalski", "Bergström", "Nkosi", "Duarte"]


def recency_weights(quarters: int = 8) -> list[float]:
    """Normalised exponential decay, most recent quarter first."""
    raw = [0.75 ** i for i in range(quarters)]
    total = sum(raw)
    return [r / total for r in raw]


def allocate_interactions(total: int, anchors: list[str], dense_anchor: str,
                          dense_share: float) -> dict[str, int]:
    """Interactions per anchor, with one anchor deliberately concentrated."""
    dense = int(total * dense_share)
    remaining = total - dense
    others = [a for a in anchors if a != dense_anchor]
    base, extra = divmod(remaining, len(others))
    alloc = {dense_anchor: dense}
    for i, anchor in enumerate(others):
        alloc[anchor] = base + (1 if i < extra else 0)
    return alloc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    rng = random.Random(SEED)

    roster = json.loads((SCREEN / "wave10_persons.json").read_text())["persons"]
    people_by_lei: dict[str, list[dict]] = {}
    for person in roster:
        if person["owner_kind"] != "natural":
            continue
        for role in person["roles"]:
            people_by_lei.setdefault(role["lei"], []).append(person)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei FROM "{PG_SCHEMA_V2}".legal_entity '
                    "WHERE is_anchor ORDER BY lei")
        anchors = [r[0] for r in cur.fetchall()]
        cur.execute(f'SELECT deal_id, lei FROM "{PG_SCHEMA_V2}".deal')
        deals_by_lei: dict[str, list[str]] = {}
        for deal_id, lei in cur.fetchall():
            deals_by_lei.setdefault(lei, []).append(deal_id)

    # The dense anchor is the one with the most client-side people, so the
    # concentration is plausible rather than arbitrary.
    dense_anchor = max(anchors, key=lambda l: len(people_by_lei.get(l, [])))

    bankers = [{
        "banker_id": f"BKR{i:03d}",
        "full_name": f"{rng.choice(FIRST)} {rng.choice(LAST)}",
        "role": ROLES[i % len(ROLES)],
        "seniority": rng.choice(SENIORITY),
        "desk": rng.choice(["CIB Coverage", "Leveraged Finance", "Treasury Services",
                            "Credit Risk", "M&A Advisory"]),
        "provenance": "synthetic — internal",
    } for i in range(BANKER_COUNT)]

    assignments = []
    for lei in anchors:
        primary = rng.choice([b for b in bankers if b["role"] == "coverage"])
        assignments.append({"banker_id": primary["banker_id"], "lei": lei,
                            "is_primary": True,
                            "assigned_date": str(date(2024, 1, 15)),
                            "provenance": "synthetic — internal"})
        for extra in rng.sample([b for b in bankers
                                 if b["banker_id"] != primary["banker_id"]], 2):
            assignments.append({"banker_id": extra["banker_id"], "lei": lei,
                                "is_primary": False,
                                "assigned_date": str(date(2024, 6, 1)),
                                "provenance": "synthetic — internal"})

    alloc = allocate_interactions(INTERACTION_TOTAL, anchors, dense_anchor, DENSE_SHARE)
    weights = recency_weights(quarters=MONTHS // 3)
    today = date(2026, 8, 18)

    # Coverage gaps: senior client officers deliberately excluded from every
    # interaction. §F wants >= 3, and the gap IS the insight the product sells.
    gap_people: list[dict] = []
    for lei in anchors:
        seniors = [p for p in people_by_lei.get(lei, [])
                   if any(r.get("officer_title") for r in p["roles"])]
        if seniors and len(gap_people) < COVERAGE_GAP_COUNT:
            gap_people.append({"person_key": seniors[0]["person_key"], "lei": lei,
                               "provenance": "synthetic — engineered",
                               "note": "withheld from every interaction to create "
                                       "a coverage gap"})
    gap_keys = {g["person_key"] for g in gap_people}

    interactions, participants = [], []
    counter = 0
    for lei, count in alloc.items():
        eligible = [p for p in people_by_lei.get(lei, [])
                    if p["person_key"] not in gap_keys]
        covering = [a["banker_id"] for a in assignments if a["lei"] == lei]
        if not eligible or not covering:
            continue
        for _ in range(count):
            counter += 1
            quarter = rng.choices(range(len(weights)), weights=weights, k=1)[0]
            day_offset = quarter * 91 + rng.randrange(91)
            interaction_id = f"INT-W10-{counter:05d}"
            deals = deals_by_lei.get(lei, [])
            interactions.append({
                "interaction_id": interaction_id,
                "lei": lei,
                "deal_id": rng.choice(deals) if deals and rng.random() < 0.25 else None,
                "interaction_type": rng.choice(["client_meeting", "diligence_call",
                                                "pitch", "check_in"]),
                "channel": rng.choice(CHANNELS),
                "subject": "client coverage interaction",
                "interaction_date": str(today - timedelta(days=day_offset)),
                "mnpi_bearing": False,
                "need_to_know": False,
                "provenance": "synthetic — internal",
            })
            for person in rng.sample(eligible, min(len(eligible), rng.randint(1, 3))):
                participants.append({"interaction_id": interaction_id,
                                     "party_kind": "person",
                                     "party_key": person["person_key"],
                                     "provenance": "synthetic — internal"})
            for banker_id in rng.sample(covering, min(len(covering), 2)):
                participants.append({"interaction_id": interaction_id,
                                     "party_kind": "banker",
                                     "party_key": banker_id,
                                     "provenance": "synthetic — internal"})

    for interaction in rng.sample(interactions, NEED_TO_KNOW_COUNT):
        interaction["need_to_know"] = True
        interaction["provenance"] = "synthetic — engineered"

    weights_rows = [
        {"weight_name": name, "weight_value": value, "policy_version": "v1.0.0",
         "effective_date": "2026-01-01", "provenance": "synthetic — internal"}
        for name, value in [("recency_half_life_days", 90.0),
                            ("frequency_weight", 0.35),
                            ("seniority_weight", 0.25),
                            ("channel_meeting_weight", 1.0),
                            ("channel_call_weight", 0.6),
                            ("channel_email_weight", 0.3)]]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": SEED,
        "dense_anchor": dense_anchor,
        "bankers": bankers,
        "coverage_assignments": assignments,
        "interactions": interactions,
        "participants": participants,
        "scoring_weights": weights_rows,
        "coverage_gaps": gap_people,
    }
    print(f"  {len(bankers)} bankers · {len(assignments)} assignments · "
          f"{len(interactions)} interactions · {len(participants)} participants")
    print(f"  dense anchor {dense_anchor}: {alloc[dense_anchor]} interactions")
    print(f"  coverage gaps: {len(gap_people)} · need-to-know: {NEED_TO_KNOW_COUNT}")

    if args.dry_run:
        print("  [dry-run] nothing written")
        return 0
    (SCREEN / "wave10_coverage.json").write_text(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run validators/test_coverage_shape.py`
Expected: PASS — `9/9 cases behave as specified`

- [ ] **Step 5: Generate**

```bash
uv run generators/generate_coverage.py --dry-run
uv run generators/generate_coverage.py
```

Expected: 40 bankers, ~2,000 interactions, 3 coverage gaps, the dense anchor reported with ≥ 200 interactions.

- [ ] **Step 6: Commit**

```bash
git add generators/generate_coverage.py validators/test_coverage_shape.py \
        sources/screening/wave10_coverage.json
git commit -m "Wave 10: generate the bank side, shaped for recency and truncation"
```

---

### Task 8: Load Postgres

**Files:**
- Create: `loaders/load_postgres_wave10.py`
- Modify: `ccf_v2.interaction` (add three columns)

**Interfaces:**
- Consumes: `wave10_persons.json`, `wave10_name_variants.json`, `wave10_appointments.json`, `wave10_holders.json`, `wave10_crosswalk.json`, `wave10_coverage.json`.
- Produces: nine new tables plus three columns on `interaction`. Later tasks read `ccf_v2.person`, `ccf_v2.banker`, `ccf_v2.interaction_participant`.

- [ ] **Step 1: Write the loader**

Create `loaders/load_postgres_wave10.py`:

```python
#!/usr/bin/env python3
"""Wave 10 — every client-360 attribute lands in Postgres.

Single-writer discipline: Postgres owns `E` and `P`, Fluree owns `R`. A Fluree
Person node carries a URI, a type and a display label; role, title, dates and
match confidence all resolve from here.

`interaction` and `deal` are EXTENDED, not duplicated. Wave 7 created them for
mnpi-wall-enforcement with 50 and 32 rows; Wave 10 grows `interaction` to
~2,000. Growing a table another wave owns is correct; creating a second
interaction table would not be.

    uv run loaders/load_postgres_wave10.py --dry-run
    uv run loaders/load_postgres_wave10.py

Idempotent: every write is an upsert on a natural key.
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
S = PG_SCHEMA_V2

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".person (
    person_key         TEXT PRIMARY KEY,
    person_key_source  TEXT NOT NULL CHECK (person_key_source IN ('sec_cik','minted')),
    cik                TEXT,
    name_as_filed      TEXT NOT NULL,
    display_name       TEXT NOT NULL,
    owner_kind         TEXT NOT NULL CHECK (owner_kind IN ('natural','entity')),
    name_last          TEXT, name_first TEXT, name_middle TEXT, name_suffix TEXT,
    provenance         TEXT NOT NULL,
    source             TEXT, retrieved_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "{S}".person_role (
    person_key      TEXT NOT NULL REFERENCES "{S}".person(person_key),
    lei             TEXT NOT NULL,
    role            TEXT NOT NULL
                    CHECK (role IN ('director','officer','ten_percent_owner')),
    officer_title   TEXT,
    first_seen      DATE, last_seen DATE,
    appointment_date DATE, appointment_source TEXT,
    provenance      TEXT NOT NULL,
    PRIMARY KEY (person_key, lei, role)
);

CREATE TABLE IF NOT EXISTS "{S}".person_name_variant (
    person_key   TEXT NOT NULL REFERENCES "{S}".person(person_key),
    variant_name TEXT NOT NULL,
    source       TEXT NOT NULL,
    rendering    TEXT,
    provenance   TEXT NOT NULL,
    PRIMARY KEY (person_key, variant_name, source)
);

CREATE TABLE IF NOT EXISTS "{S}".person_crosswalk (
    source_system TEXT NOT NULL,
    source_id     TEXT NOT NULL,
    source_name   TEXT,
    person_key    TEXT NOT NULL REFERENCES "{S}".person(person_key),
    match_score   NUMERIC(6,4),
    match_band    TEXT NOT NULL
                  CHECK (match_band IN ('exact','strong','weak','false_positive')),
    is_true_match BOOLEAN NOT NULL,
    provenance    TEXT NOT NULL,
    note          TEXT,
    PRIMARY KEY (source_system, source_id, person_key)
);

CREATE TABLE IF NOT EXISTS "{S}".institutional_holder (
    lei                TEXT NOT NULL,
    manager_cik        TEXT NOT NULL,
    manager_name       TEXT,
    cusip              TEXT NOT NULL,
    value_usd          NUMERIC,
    shares             NUMERIC,
    report_period      TEXT,
    issuer_match_score NUMERIC(6,4),
    issuer_match_band  TEXT,
    provenance         TEXT NOT NULL,
    PRIMARY KEY (lei, manager_cik, cusip, report_period)
);

CREATE TABLE IF NOT EXISTS "{S}".banker (
    banker_id  TEXT PRIMARY KEY,
    full_name  TEXT NOT NULL,
    role       TEXT NOT NULL CHECK (role IN ('coverage','product','credit')),
    seniority  TEXT NOT NULL,
    desk       TEXT,
    provenance TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".coverage_assignment (
    banker_id     TEXT NOT NULL REFERENCES "{S}".banker(banker_id),
    lei           TEXT NOT NULL,
    is_primary    BOOLEAN NOT NULL DEFAULT FALSE,
    assigned_date DATE,
    provenance    TEXT NOT NULL,
    PRIMARY KEY (banker_id, lei)
);

CREATE TABLE IF NOT EXISTS "{S}".interaction_participant (
    interaction_id TEXT NOT NULL,
    party_kind     TEXT NOT NULL CHECK (party_kind IN ('person','banker')),
    party_key      TEXT NOT NULL,
    provenance     TEXT NOT NULL,
    PRIMARY KEY (interaction_id, party_kind, party_key)
);

CREATE TABLE IF NOT EXISTS "{S}".scoring_weight (
    weight_name    TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    weight_value   NUMERIC NOT NULL,
    effective_date DATE,
    provenance     TEXT NOT NULL,
    PRIMARY KEY (weight_name, policy_version)
);

ALTER TABLE "{S}".interaction ADD COLUMN IF NOT EXISTS channel TEXT;
ALTER TABLE "{S}".interaction ADD COLUMN IF NOT EXISTS subject TEXT;
ALTER TABLE "{S}".interaction ADD COLUMN IF NOT EXISTS need_to_know BOOLEAN
    NOT NULL DEFAULT FALSE;

ALTER TABLE "{S}".context_debt ADD COLUMN IF NOT EXISTS subject_kind TEXT;
ALTER TABLE "{S}".context_debt ADD COLUMN IF NOT EXISTS subject_key  TEXT;

CREATE INDEX IF NOT EXISTS ix_person_role_lei      ON "{S}".person_role (lei);
CREATE INDEX IF NOT EXISTS ix_participant_party    ON "{S}".interaction_participant (party_kind, party_key);
CREATE INDEX IF NOT EXISTS ix_interaction_lei_date ON "{S}".interaction (lei, interaction_date DESC);
"""


def load(path: str, key: str):
    return json.loads((SCREEN / path).read_text())[key]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    persons = load("wave10_persons.json", "persons")
    variants = load("wave10_name_variants.json", "variants")
    appointments = load("wave10_appointments.json", "appointments")
    holders = load("wave10_holders.json", "holders")
    crosswalk = load("wave10_crosswalk.json", "rows")
    coverage = json.loads((SCREEN / "wave10_coverage.json").read_text())

    counts = {
        "person": len(persons), "person_role": sum(len(p["roles"]) for p in persons),
        "person_name_variant": len(variants), "person_crosswalk": len(crosswalk),
        "institutional_holder": len(holders), "banker": len(coverage["bankers"]),
        "coverage_assignment": len(coverage["coverage_assignments"]),
        "interaction (new)": len(coverage["interactions"]),
        "interaction_participant": len(coverage["participants"]),
        "scoring_weight": len(coverage["scoring_weights"]),
    }
    for table, n in counts.items():
        print(f"  {table:26} {n:>6}")

    if args.dry_run:
        print("  [dry-run] no DDL executed, no rows written")
        return 0

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)

        cur.executemany(
            f'INSERT INTO "{S}".person (person_key, person_key_source, cik, '
            "name_as_filed, display_name, owner_kind, name_last, name_first, "
            "name_middle, name_suffix, provenance, source) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (person_key) DO UPDATE SET "
            "display_name = EXCLUDED.display_name, owner_kind = EXCLUDED.owner_kind",
            [(p["person_key"], p["person_key_source"], p["cik"], p["name_as_filed"],
              p["display_name"], p["owner_kind"], p["last"], p["first"],
              p["middle"], p["suffix"], "public", "SEC EDGAR Form 4")
             for p in persons])

        appt = {(a["person_key"], a["lei"]): a for a in appointments}
        cur.executemany(
            f'INSERT INTO "{S}".person_role (person_key, lei, role, officer_title, '
            "first_seen, last_seen, appointment_date, appointment_source, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (person_key, lei, role) DO UPDATE SET "
            "officer_title = COALESCE(EXCLUDED.officer_title, "
            f'"{S}".person_role.officer_title), '
            "last_seen = GREATEST(EXCLUDED.last_seen, "
            f'"{S}".person_role.last_seen)',
            [(p["person_key"], r["lei"], r["role"], r["officer_title"],
              r["first_seen"], r["last_seen"],
              appt.get((p["person_key"], r["lei"]), {}).get("appointment_date"),
              "8-K Item 5.02" if (p["person_key"], r["lei"]) in appt else None,
              "public")
             for p in persons for r in p["roles"]])

        cur.executemany(
            f'INSERT INTO "{S}".person_name_variant '
            "(person_key, variant_name, source, rendering, provenance) "
            "VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            [(v["person_key"], v["variant_name"], v["source"], v["rendering"],
              v["provenance"]) for v in variants])

        cur.executemany(
            f'INSERT INTO "{S}".person_crosswalk (source_system, source_id, '
            "source_name, person_key, match_score, match_band, is_true_match, "
            "provenance, note) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (source_system, source_id, person_key) DO UPDATE SET "
            "match_band = EXCLUDED.match_band, match_score = EXCLUDED.match_score",
            [(c["source_system"], c["source_id"], c["source_name"], c["person_key"],
              c["match_score"], c["match_band"], c["is_true_match"],
              c["provenance"], c["note"]) for c in crosswalk])

        cur.executemany(
            f'INSERT INTO "{S}".institutional_holder (lei, manager_cik, manager_name, '
            "cusip, value_usd, shares, report_period, issuer_match_score, "
            "issuer_match_band, provenance) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT DO NOTHING",
            [(h["lei"], h["manager_cik"], h["manager_name"], h["cusip"],
              h["value_usd"] or None, h["shares"] or None, h["report_period"],
              h["issuer_match_score"], h["issuer_match_band"], h["provenance"])
             for h in holders])

        cur.executemany(
            f'INSERT INTO "{S}".banker (banker_id, full_name, role, seniority, '
            "desk, provenance) VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (banker_id) DO NOTHING",
            [(b["banker_id"], b["full_name"], b["role"], b["seniority"], b["desk"],
              b["provenance"]) for b in coverage["bankers"]])

        cur.executemany(
            f'INSERT INTO "{S}".coverage_assignment (banker_id, lei, is_primary, '
            "assigned_date, provenance) VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (banker_id, lei) DO NOTHING",
            [(a["banker_id"], a["lei"], a["is_primary"], a["assigned_date"],
              a["provenance"]) for a in coverage["coverage_assignments"]])

        cur.executemany(
            f'INSERT INTO "{S}".interaction (interaction_id, lei, deal_id, '
            "interaction_type, interaction_date, mnpi_bearing, provenance, "
            "channel, subject, need_to_know) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (interaction_id) DO UPDATE SET "
            "need_to_know = EXCLUDED.need_to_know, channel = EXCLUDED.channel",
            [(i["interaction_id"], i["lei"], i["deal_id"], i["interaction_type"],
              i["interaction_date"], i["mnpi_bearing"], i["provenance"],
              i["channel"], i["subject"], i["need_to_know"])
             for i in coverage["interactions"]])

        cur.executemany(
            f'INSERT INTO "{S}".interaction_participant '
            "(interaction_id, party_kind, party_key, provenance) "
            "VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            [(p["interaction_id"], p["party_kind"], p["party_key"], p["provenance"])
             for p in coverage["participants"]])

        # Design §7.2: a roster member for whom NO document rendering was found
        # is Context Debt, not a silent gap. `context_debt` was covenant-shaped
        # until this wave widened it; the register is estate-wide, so one table
        # carries both rather than each wave minting its own.
        rendered = {v["person_key"] for v in variants}
        cur.executemany(
            f'INSERT INTO "{S}".context_debt (accession, covenant_type, reason, '
            "recorded_at, subject_kind, subject_key) "
            "VALUES (%s,%s,%s,current_date,%s,%s) ON CONFLICT DO NOTHING",
            [(None, None,
              "no DEF 14A or 8-K rendering found for a Form 4 roster member; "
              "bounded search returned nothing, so no variant is asserted",
              "person", p["person_key"])
             for p in persons
             if p["owner_kind"] == "natural" and p["person_key"] not in rendered])

        cur.executemany(
            f'INSERT INTO "{S}".scoring_weight (weight_name, policy_version, '
            "weight_value, effective_date, provenance) VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (weight_name, policy_version) DO UPDATE SET "
            "weight_value = EXCLUDED.weight_value",
            [(w["weight_name"], w["policy_version"], w["weight_value"],
              w["effective_date"], w["provenance"])
             for w in coverage["scoring_weights"]])
        conn.commit()

    print("  loaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

> **A consequence of the bounded search, stated rather than hidden.** Design §3.1
> provides `person_key_source = 'minted'` for officers named in DEF 14A who never
> file a Form 4. Under the §2 inversion, DEF 14A is searched only for names
> already held, so **no minted key is created by this pipeline** — every person
> in the estate is a real Form 4 filer keyed on a real CIK.
>
> That is the accepted cost of the inversion: officers below the Form 4 reporting
> threshold are not captured. The column and the `syn-p-` helper stay, because
> the distinction they record is real and Wave 13's PSC work will need it. If
> `SELECT count(*) FROM person WHERE person_key_source = 'minted'` returns 0
> after this load, **that is the expected result, not a bug.**

- [ ] **Step 2: Dry run, then load, then re-run for idempotency**

```bash
uv run loaders/load_postgres_wave10.py --dry-run
uv run loaders/load_postgres_wave10.py
uv run loaders/load_postgres_wave10.py    # second run must change nothing
```

Expected: identical counts on both real runs. A row-count change on the second run is an idempotency bug — fix before continuing.

- [ ] **Step 3: Verify the interaction table grew without disturbing Wave 7**

```bash
uv run python -c "
from ccf.config import pg_connect, PG_SCHEMA_V2 as S
with pg_connect() as c, c.cursor() as cur:
    cur.execute(f'SELECT count(*) FROM \"{S}\".interaction')
    print('interactions:', cur.fetchone()[0])
    cur.execute(f'SELECT count(*) FROM \"{S}\".interaction WHERE mnpi_bearing')
    print('mnpi-bearing (Wave 7, must be unchanged):', cur.fetchone()[0])
    cur.execute(f'SELECT count(*) FROM \"{S}\".person WHERE owner_kind = %s', ('natural',))
    print('natural persons:', cur.fetchone()[0])"
```

Expected: ~2,050 interactions; the **mnpi-bearing count must equal its pre-Wave-10 value** — Wave 10 sets `need_to_know`, never `mnpi_bearing`.

- [ ] **Step 4: Commit**

```bash
git add loaders/load_postgres_wave10.py
git commit -m "Wave 10: load the person layer and bank side into Postgres"
```

---

### Task 9: Load Fluree

**Files:**
- Create: `loaders/load_fluree_wave10.py`

**Interfaces:**
- Consumes: `ccf_v2.person`, `ccf_v2.person_role`, `ccf_v2.banker`, `ccf_v2.coverage_assignment`, `ccf_v2.interaction`, `ccf_v2.interaction_participant`; `loaders.load_collateral_wave9.entity_uri_by_lei`.
- Produces: typed nodes and six edge predicates in ledger `fibo-v2`.

- [ ] **Step 1: Write the loader**

Create `loaders/load_fluree_wave10.py`:

```python
#!/usr/bin/env python3
"""Wave 10 — the client-360 edges, in Fluree.

Three of the six relationships have a real FIBO property; three do not. Verified
against the Wave 8 binding contract, which bound all ten officer, director and
employment terms:

    employedBy     -> fibo-fnd-org-fm:isEmployedBy      REAL FIBO term
    officer of     -> fibo-be-oac-exec:isOfficerOf      REAL FIBO term
    director of    -> fibo-be-oac-exec:isDirectorOf     REAL FIBO term
    coversClient   -> ex:coversClient                   no FIBO equivalent
    participatedIn -> ex:participatedIn                 no FIBO equivalent
    relatedToDeal  -> ex:relatedToDeal                  no FIBO equivalent

THIRD consecutive wave where FIBO has no vocabulary for the bank's own
operational relations — Covenant in Wave 5, pledgedBy/setOffAgainst/nettedUnder
in Wave 9, coverage and interaction now. That goes to the vault as one pattern.

FIBO has `CorporateOfficer` as a class but NO `Director` class — directorship is
only an edge, and `BoardOfDirectors` is the board, not the person. `ex:Director`
is deliberately NOT minted to make the model look symmetric.

Fluree has no OWL inference, so every node is typed explicitly for every role it
is queried against.

    uv run loaders/load_fluree_wave10.py --dry-run
    uv run loaders/load_fluree_wave10.py
"""

from __future__ import annotations

import argparse
import sys

from ccf import fluree
from ccf.config import EX, PG_SCHEMA_V2, pg_connect
from loaders.load_collateral_wave9 import entity_uri_by_lei, triple, uri

FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

C_PERSON = f"{FIBO}FND/AgentsAndPeople/People/Person"
C_OFFICER = f"{FIBO}BE/OwnershipAndControl/Executives/CorporateOfficer"
P_EMPLOYED_BY = f"{FIBO}FND/Organizations/FormalOrganizations/isEmployedBy"
P_OFFICER_OF = f"{FIBO}BE/OwnershipAndControl/Executives/isOfficerOf"
P_DIRECTOR_OF = f"{FIBO}BE/OwnershipAndControl/Executives/isDirectorOf"

C_BANKER = f"{EX}Banker"
C_INTERACTION = f"{EX}Interaction"
C_DEAL = f"{EX}Deal"
P_COVERS_CLIENT = f"{EX}coversClient"
P_PARTICIPATED_IN = f"{EX}participatedIn"
P_RELATED_TO_DEAL = f"{EX}relatedToDeal"

BATCH = 500


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    entity_uri = entity_uri_by_lei()
    print(f"  resolved {len(entity_uri)} entity nodes from the ledger")

    S = PG_SCHEMA_V2
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT person_key, display_name FROM "{S}".person '
                    "WHERE owner_kind = 'natural'")
        people = cur.fetchall()
        cur.execute(f'SELECT person_key, lei, role FROM "{S}".person_role r '
                    f'WHERE EXISTS (SELECT 1 FROM "{S}".person p '
                    "WHERE p.person_key = r.person_key AND p.owner_kind = 'natural')")
        roles = cur.fetchall()
        cur.execute(f'SELECT banker_id, full_name FROM "{S}".banker')
        bankers = cur.fetchall()
        cur.execute(f'SELECT banker_id, lei FROM "{S}".coverage_assignment')
        assignments = cur.fetchall()
        cur.execute(f'SELECT interaction_id, deal_id FROM "{S}".interaction')
        interactions = cur.fetchall()
        cur.execute(f'SELECT deal_id FROM "{S}".deal')
        deals = [r[0] for r in cur.fetchall()]
        cur.execute(f'SELECT interaction_id, party_kind, party_key '
                    f'FROM "{S}".interaction_participant')
        participants = cur.fetchall()

    triples: list[str] = []

    for cls in (C_BANKER, C_INTERACTION, C_DEAL):
        triples.append(triple(cls, RDF_TYPE, "http://www.w3.org/2002/07/owl#Class"))
        triples.append(triple(cls, RDFS_LABEL, cls.rsplit("/", 1)[-1], literal=True))

    person_uri = {}
    for person_key, display_name in people:
        node = uri(f"person-{person_key}")
        person_uri[person_key] = node
        triples.append(triple(node, RDF_TYPE, C_PERSON))
        triples.append(triple(node, RDFS_LABEL, display_name, literal=True))

    officers = {k for k, _, role in roles if role == "officer"}
    for person_key in officers & person_uri.keys():
        triples.append(triple(person_uri[person_key], RDF_TYPE, C_OFFICER))

    banker_uri = {}
    for banker_id, full_name in bankers:
        node = uri(f"banker-{banker_id}")
        banker_uri[banker_id] = node
        triples.append(triple(node, RDF_TYPE, C_BANKER))
        triples.append(triple(node, RDFS_LABEL, full_name, literal=True))

    interaction_uri = {}
    for interaction_id, _ in interactions:
        node = uri(f"interaction-{interaction_id}")
        interaction_uri[interaction_id] = node
        triples.append(triple(node, RDF_TYPE, C_INTERACTION))
        triples.append(triple(node, RDFS_LABEL, interaction_id, literal=True))

    deal_uri = {}
    for deal_id in deals:
        node = uri(f"deal-{deal_id}")
        deal_uri[deal_id] = node
        triples.append(triple(node, RDF_TYPE, C_DEAL))
        triples.append(triple(node, RDFS_LABEL, deal_id, literal=True))

    # ---- edges. Every target is resolved, never constructed. -----------------
    dangling = 0
    for person_key, lei, role in roles:
        subject = person_uri.get(person_key)
        target = entity_uri.get(lei)
        if subject is None or target is None:
            dangling += 1
            continue
        triples.append(triple(subject, P_EMPLOYED_BY, target))
        if role == "officer":
            triples.append(triple(subject, P_OFFICER_OF, target))
        elif role == "director":
            triples.append(triple(subject, P_DIRECTOR_OF, target))

    for banker_id, lei in assignments:
        subject, target = banker_uri.get(banker_id), entity_uri.get(lei)
        if subject is None or target is None:
            dangling += 1
            continue
        triples.append(triple(subject, P_COVERS_CLIENT, target))

    for interaction_id, party_kind, party_key in participants:
        target = interaction_uri.get(interaction_id)
        subject = (person_uri if party_kind == "person" else banker_uri).get(party_key)
        if subject is None or target is None:
            dangling += 1
            continue
        triples.append(triple(subject, P_PARTICIPATED_IN, target))

    for interaction_id, deal_id in interactions:
        if not deal_id:
            continue
        subject, target = interaction_uri.get(interaction_id), deal_uri.get(deal_id)
        if subject is None or target is None:
            dangling += 1
            continue
        triples.append(triple(subject, P_RELATED_TO_DEAL, target))

    print(f"  {len(triples)} triples · {dangling} skipped for an unresolved endpoint")
    if dangling:
        print("  NOTE: skipped rather than pointed at a constructed URI. "
              "A constructed URI cannot fail loudly — see Wave 9.")

    if args.dry_run:
        print("  [dry-run] nothing written to Fluree")
        return 0

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")
    print(f"  ledger now at t={fluree.ledger_t()} · "
          f"{fluree.count_triples():,} triples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Dry run, load, re-run**

```bash
uv run loaders/load_fluree_wave10.py --dry-run
uv run loaders/load_fluree_wave10.py
uv run loaders/load_fluree_wave10.py    # INSERT DATA of stable triples: t advances, triple count does not
```

Expected: `dangling` should be **0**. Any non-zero value means a person or banker exists in Postgres whose node was not created — investigate before proceeding, do not accept the skip.

- [ ] **Step 3: Commit**

```bash
git add loaders/load_fluree_wave10.py
git commit -m "Wave 10: load the coverage graph edges into Fluree"
```

---

### Task 10: Validators — partition, conditions, traversal, and the Wave 7 regression

**Files:**
- Create: `validators/traversal.py`
- Modify: `validators/partition.py`
- Modify: `validators/conditions.py`

**Interfaces:**
- Consumes: everything loaded in Tasks 8 and 9.
- Produces: `partition.py` at 13/13, `conditions.py` with eight new checks, `traversal.py` proving the depth-2 truncation case.

- [ ] **Step 1: Write the truncation proof**

Create `validators/traversal.py`:

```python
#!/usr/bin/env python3
"""§F: >= 1 client whose depth-2 traversal exceeds `limit=200`.

This condition CANNOT be established by counting. §D step 3 requires the limit
be applied INSIDE the traversal, ordered by recency — "fetching 5,000 nodes and
truncating to 200 in memory satisfies the contract and defeats its purpose". So
the proof has to be an actual bounded traversal.

Depth 1 from the client entity reaches people (isEmployedBy, inverse) and
bankers (coversClient, inverse). Depth 2 reaches the interactions those parties
participated in. The node set is the union.

    uv run validators/traversal.py
"""

from __future__ import annotations

import sys

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, pg_connect

LIMIT = 200
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"


def depth2_nodes(entity_uri: str) -> set[str]:
    """Every node reachable within two hops of one client entity."""
    sparql = f"""
    SELECT DISTINCT ?node FROM <{FLUREE_LEDGER_V2}> WHERE {{
      {{ ?node <{FIBO}FND/Organizations/FormalOrganizations/isEmployedBy>
               <{entity_uri}> }}
      UNION
      {{ ?node <{EX}coversClient> <{entity_uri}> }}
      UNION
      {{ ?party <{FIBO}FND/Organizations/FormalOrganizations/isEmployedBy>
                <{entity_uri}> .
         ?party <{EX}participatedIn> ?node }}
      UNION
      {{ ?party <{EX}coversClient> <{entity_uri}> .
         ?party <{EX}participatedIn> ?node }}
    }}
    """
    rows = fluree.query(sparql).get("results", {}).get("bindings", [])
    return {r["node"]["value"] for r in rows}


def main() -> int:
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, count(*) AS n FROM "{PG_SCHEMA_V2}".interaction '
                    "GROUP BY lei ORDER BY n DESC LIMIT 5")
        candidates = cur.fetchall()

    from loaders.load_collateral_wave9 import entity_uri_by_lei
    entity_uri = entity_uri_by_lei()

    print(f"\n  DEPTH-2 TRAVERSAL vs limit={LIMIT}\n")
    exceeded = []
    for lei, interaction_count in candidates:
        node = entity_uri.get(lei)
        if node is None:
            print(f"  [skip] {lei}: no entity node in the ledger")
            continue
        nodes = depth2_nodes(node)
        over = len(nodes) > LIMIT
        exceeded.append(lei) if over else None
        print(f"  [{'ok  ' if over else '    '}] {lei}: {len(nodes):>4} nodes at "
              f"depth 2  ({interaction_count} interactions)")

    ok = len(exceeded) >= 1
    print(f"\n  {len(exceeded)} client(s) exceed limit={LIMIT} — §F wants >= 1: "
          f"{'PASS' if ok else 'FAIL'}\n")
    if not ok:
        print("  Truncation disclosure is unexercised. Raise the dense anchor's "
              "share in generate_coverage.py; do NOT lower the limit.\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it**

Run: `uv run validators/traversal.py`
Expected: at least one client above 200. If none, raise `DENSE_SHARE` in `generate_coverage.py`, regenerate, reload, re-run. **Never lower `LIMIT`** — the limit is the spec's, not ours.

- [ ] **Step 3: Extend the partition validator**

`validators/partition.py` builds a `list[Result]` per store, where
`Result(check, store, passed, detail)`. Register `ex:Banker`, `ex:Interaction`
and `ex:Deal` alongside the seven permitted extensions already there, then add
one check to `check_fluree()` and one to `check_postgres()`.

In `check_fluree()`:

```python
    # Single-writer, checked rather than trusted. A Person, Banker, Interaction
    # or Deal node may carry a type, a label, and the six Wave 10 edges — and
    # nothing else. Every attribute resolves from Postgres.
    permitted = ", ".join(f"<{u}>" for u in (
        RDF_TYPE, RDFS_LABEL,
        f"{FIBO}FND/Organizations/FormalOrganizations/isEmployedBy",
        f"{FIBO}BE/OwnershipAndControl/Executives/isOfficerOf",
        f"{FIBO}BE/OwnershipAndControl/Executives/isDirectorOf",
        f"{EX}coversClient", f"{EX}participatedIn", f"{EX}relatedToDeal"))
    types = ", ".join(f"<{u}>" for u in (
        f"{FIBO}FND/AgentsAndPeople/People/Person",
        f"{FIBO}BE/OwnershipAndControl/Executives/CorporateOfficer",
        f"{EX}Banker", f"{EX}Interaction", f"{EX}Deal"))
    rows = bindings(sparql(f"""
        SELECT ?s ?p FROM <{FLUREE_LEDGER_V2}> WHERE {{
          ?s a ?t . ?s ?p ?o .
          FILTER(?t IN ({types}))
          FILTER(?p NOT IN ({permitted}))
        }} LIMIT 5
    """))
    out.append(Result(
        "no client-360 attribute in the graph", "fluree", not rows,
        "clean" if not rows
        else f"{rows[0]['p']['value'].rsplit('/', 1)[-1]} on {len(rows)}+ nodes"))
```

In `check_postgres()`, inside the existing `with pg_connect()` block:

```python
            # Every Fluree Person must resolve to a Postgres row. The reverse is
            # NOT required: corporate reporting owners are stored with
            # owner_kind='entity' and deliberately never become Person nodes.
            if "person" in tables:
                cur.execute(f'SELECT person_key FROM "{PG_SCHEMA_V2}".person')
                known = {r[0] for r in cur.fetchall()}
                graph = {b["s"]["value"].rsplit("/", 1)[-1].removeprefix("person-")
                         for b in bindings(sparql(f"""
                             SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{
                               ?s a <{FIBO}FND/AgentsAndPeople/People/Person> }}"""))}
                orphans = graph - known
                out.append(Result(
                    "every Fluree person resolves to a row", "postgres",
                    not orphans,
                    "all resolve" if not orphans
                    else f"{len(orphans)} orphaned, e.g. {sorted(orphans)[0]}"))
```

- [ ] **Step 4: Add the eight condition checks**

In `validators/conditions.py`, add a `client-360-coverage-graph` section:

| Check | Query | Floor |
|---|---|---|
| anchors with 8–25 named people | `person_role` grouped by `lei`, natural persons only | ≥ 45 anchors in band |
| synthetic bankers | `count(*) FROM banker` | ≥ 40 |
| interaction records | `count(*) FROM interaction` | ≥ 2000 |
| **recency gradient** | newest-quarter count vs oldest-quarter count | newest ≥ 2× oldest |
| **depth-2 over limit** | delegate to `validators/traversal.py` | ≥ 1 |
| name variants | distinct `person_key` in `person_name_variant` | ≥ 5 |
| coverage gaps | senior officers with no row in `interaction_participant` | ≥ 3 |
| need-to-know interactions | `count(*) FROM interaction WHERE need_to_know` | ≥ 10 |
| **false-positive pair** | `person_crosswalk WHERE match_band = 'false_positive'` | ≥ 1 |

The recency check, written out because it is the one that counting fakes:

```python
    cur.execute(f"""
        SELECT
          count(*) FILTER (WHERE interaction_date >= current_date - 91)  AS newest,
          count(*) FILTER (WHERE interaction_date <  current_date - 638) AS oldest
        FROM "{PG_SCHEMA_V2}".interaction
        WHERE provenance LIKE 'synthetic%'
    """)
    newest, oldest = cur.fetchone()
    condition("recency gradient, newest vs oldest quarter", newest, max(oldest * 2, 1),
              note="a flat distribution satisfies the count and makes the "
                   "relationship score meaningless")
```

- [ ] **Step 5: Run the full validator suite**

```bash
uv run validators/partition.py      # expect 13/13
uv run validators/conditions.py     # expect 69 passed, 1 failed (the §0.4 control-edge gap)
uv run validators/traversal.py      # expect >= 1 client over 200
uv run validators/projection.py     # WAVE 7 REGRESSION CHECK — expect 3 issuers, 3 shapes
uv run validators/bitemporal.py     # expect 3/3 unchanged
```

**`projection.py` is the gate that matters here.** `interaction` grew 40×. Its
assertion is that three principals yield three *different* shapes, not fixed
counts, so growth should be safe — but if the shapes stop diverging,
**constrain the generator, do not relax the validator.** The likely cause would
be Wave 10 interactions swamping the MNPI-bearing signal; the fix is to reduce
non-MNPI volume on the affected issuers, not to change what `projection.py`
asserts.

- [ ] **Step 6: Commit**

```bash
git add validators/traversal.py validators/partition.py validators/conditions.py
git commit -m "Wave 10: validators for the coverage graph, incl. the truncation proof"
```

---

### Task 11: Documentation, published claims, and the vault punch list

**Files:**
- Modify: `docs/ccf_dataprep_v2.md` (entity tables, counts, the six `ex:` extensions)
- Modify: `docs/known-issues.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/data-acquisition-plan.md`
- Modify: `sources/screening/published_claims.json`
- Create: `~/.agent-exchange/ccf-dataprep/outbox/<timestamp>-wave10-drift/`

- [ ] **Step 1: Update `published_claims.json` and regenerate the punch list**

Add the terms Wave 10 materialized: `Person`, `CorporateOfficer`, `isEmployedBy`,
`isOfficerOf`, `isDirectorOf`, plus the six `ex:` extensions.

```bash
uv run validators/binding_drift.py
uv run validators/binding_drift.py --json > /tmp/wave10-drift.json
```

Expected: the Wave 10 terms appear as new disagreements, because the vault does
not yet mention them. That is the punch list generating itself, exactly as
designed.

**`binding_drift.py` reports; it does not write a punch-list file.** The
`DRIFT-PUNCHLIST.md` pair that used to live in `docs/vault-outbox/` was written
by hand and removed with that directory. So render the markdown from the JSON
into the outbox directory in Step 3 — do not look for a file the validator
never creates.

Check the direction of every disagreement before acting: `CAVEAT_STALE` means
**the estate is right and the published warning is out of date.**

- [ ] **Step 2: Update the four docs**

- `ccf_dataprep_v2.md` — entity tables, row counts, the six `ex:` extensions under the extension register. **No new FIBO bindings**, so the binding table itself is unchanged; say so explicitly rather than leaving it ambiguous.
- `known-issues.md` — record: the EDGAR rendered-view trap (§1.5 of the design); 13F issuer matching being fuzzy; any anchor shortfall from Task 3; the FIBO director-class asymmetry.
- `HANDOFF.md` — Waves 0–10 complete, new validator expectations, next step Wave 11.
- `data-acquisition-plan.md` — mark Wave 10 done, carry forward the Wave 11 entry.

- [ ] **Step 3: Send the vault punch list**

The channel is the agent exchange, **not** `docs/vault-outbox/`, which is retired.
Read section 5 of the `obsidian-vault-access` skill before the first send —
**the directory timestamp uses hyphens, never colons**, and a name outside
`[A-Za-z0-9._-]` is rejected silently.

```bash
STAMP=$(date -u +%Y-%m-%dT%H-%M-%SZ)          # hyphens only — a colon is rejected
BOX=~/.agent-exchange/ccf-dataprep/outbox/${STAMP}-wave10-drift
mkdir -p "${BOX}.tmp"
cp /tmp/wave10-drift.json "${BOX}.tmp/drift-punchlist.json"   # from Step 1

cat > "${BOX}.tmp/message.md" <<MSG
---
from: ccf-dataprep
sent_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
subject: Wave 10 term drift, and a pattern across three waves
kind: document
targets:
  - wiki/context-products/content/fibo-iri-binding.md
  - wiki/context-products/content/client-360-coverage-graph.md
---

Wave 10 loaded client-360-coverage-graph. Five bound FIBO terms moved to
materialized: Person, CorporateOfficer, isEmployedBy, isOfficerOf, isDirectorOf.
No binding was added or changed — Wave 8 had already bound everything this
product needs, and the binding table is unchanged.

Six ex: extensions were minted because FIBO has no equivalent: coversClient,
participatedIn, relatedToDeal, and the classes Banker, Interaction, Deal.

The pattern is the part worth acting on. This is the THIRD consecutive wave
needing extensions for the same reason: FIBO models instruments and agreements
but not the bank's operational relation to them. Wave 5 needed it for Covenant,
Wave 9 for pledgedBy / setOffAgainst / nettedUnder, Wave 10 for coverage and
interaction. Three separate term lists understate it; one note about the gap
does not.

This adds; it removes nothing.
MSG

mv "${BOX}.tmp" "${BOX}"                       # the rename is what publishes it
```

`message.md` frontmatter needs `from`, `sent_at`, `subject`, `kind`, and
`targets`. A submission that would REMOVE existing vault content must say so in
prose — this one adds only, and says so.

**Batch three things into one message:** the Wave 10 term drift; the still-pending
Wave 9 `DepositAccount` item if it has not been applied; and the **pattern finding** —
that three consecutive waves have needed `ex:` extensions because FIBO models
instruments and agreements but not the bank's operational relations to them.
That pattern is worth more to the vault than three separate term lists.

- [ ] **Step 4: Final verification before declaring the wave done**

```bash
uv run validators/partition.py && uv run validators/conditions.py \
  && uv run validators/traversal.py && uv run validators/projection.py \
  && uv run validators/bitemporal.py && uv run validators/binding_drift.py \
  && uv run validators/test_form4.py && uv run validators/test_persons.py \
  && uv run validators/test_renderings.py && uv run validators/test_resolve.py \
  && uv run validators/test_coverage_shape.py
```

A product is done only when all five conditions in CLAUDE.md's *Definition of
done* hold. **Hitting a count while missing a condition is a failure**, so
`traversal.py` and the recency gradient carry the same weight as the row counts.

- [ ] **Step 5: Commit**

```bash
git add docs/ sources/screening/published_claims.json
git commit -m "Wave 10 complete: client-360 coverage graph across Postgres and Fluree"
```

---

## Appendix: Facts an implementer will otherwise rediscover the hard way

1. **`primaryDocument` for a Form 4 is the rendered HTML view.** Strip the `xsl…/` prefix. It returns HTTP 200, so the failure is silent.
2. **The 13F dataset naming changed.** `<YYYY>q<N>_form13f.zip` 404s; current form is `01mar2026-31may2026_form13f.zip`.
3. **8-K item codes are in the submissions index.** Never parse an 8-K to decide whether it is an Item 5.02.
4. **Two anchors file no proxy** — `CrossAmerica Partners LP` and `GENESIS ENERGY LP`, both MLPs. Expected, not a defect.
5. **Form 4 reporting owners include corporations.** Filter on `owner_kind` before creating `Person` nodes.
6. **Fluree SPARQL needs an explicit `FROM <ledger>`** or it returns HTTP 500.
7. **Fluree is append-only.** A correction is a retraction plus an assertion; both stay in history.
8. **No OWL inference.** Type every node explicitly for every role you query.
9. **Never construct a URI for an unloaded node.** Resolve via `entity_uri_by_lei()`.
10. **`cast_audit.py` is wrong about this product** — it says non-proxy filers cannot supply client-side people. Form 4 covers all 50. Update its note.
