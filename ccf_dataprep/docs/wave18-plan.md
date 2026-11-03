# Wave 18 — `syndicated-lending-co-lender` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate our estate and the provisioned co-lender peer fabric with every element `cb.syndicate-co-lender.v1` needs, so the SDK can assemble it across an organizational boundary.

**Architecture:** Six real filed credit agreements supply public syndicate composition; we invent only what each member privately holds. Our five stores hold our slice under single-writer discipline; a second, isolated fabric holds two counterparty identities at different disclosure precisions. Every §F condition that sounds like runtime behaviour is a **declaration in data** — we build no client, no server, and no Federate operator.

**Tech Stack:** Python 3 via `uv`; PostgreSQL (`psycopg`); Fluree via SPARQL over HTTP (`ccf/fluree.py`); MongoDB (`pymongo`); SQLite (stdlib); `pytest` via `uv run --with pytest pytest`.

**Spec:** `docs/wave18-design.md` (commit `f3369a8`). Read it before Task 1 — the plan argues from it and does not restate its reasoning.

---

## Global Constraints

Every task's requirements implicitly include this section.

- **`uv run pytest` is broken repo-wide.** Always `uv run --with pytest pytest`.
- **Read the PASS count**, never the "0 failed" line — `conditions.py` can SKIP on a broken query elsewhere in the file.
- **Store identifiers come from `ccf/config.py`**, never from literals: `PG_SCHEMA_V2` (`ccf_v2`), `FLUREE_LEDGER_V2` (`fibo-v2`), `MONGO_DB_V2` (`fibo_v2`), `SQLITE_PATH`. CLAUDE.md's table still names the superseded v1 values.
- **Peer identifiers likewise**: `CO_LENDER_PG_SCHEMA` (`colender`), `CO_LENDER_FLUREE_LEDGER` (`bofa/syndicate`), `CO_LENDER_MONGO_DB`. Peer env vars come from `~/.bashrc`, which returns early for non-interactive shells — run peer work under `bash -ic` if the vars are absent.
- **Every peer write gates on three things, in order**: `assert_distinct_fabrics()`, `assert_co_lender_schema(CO_LENDER_PG_SCHEMA)`, and an explicit `SELECT current_database()` assertion. Both databases sit on `192.168.4.76:5432` and differ by nothing but a name.
- **Loaders are idempotent.** `CREATE TABLE IF NOT EXISTS` plus `INSERT ... ON CONFLICT (pk) DO UPDATE SET`. A loader owns only the columns it writes and must never name another task's column in its INSERT list or SET clause.
- **Identifiers key on content, never on row position.** Four loaders on `main` already rewrite other waves' rows when a table grows; check before adding rows.
- **Provenance strings are exactly** `public`, `synthetic — internal`, or `synthetic — engineered` (em dash, spaced). Every row of every new table carries one unless the design says otherwise.
- **Instance URIs stay under `http://example.org/fibo/`.** Real LEIs live in the `lei` attribute, never in the URI.
- **Fluree runs without OWL inference.** Type every node explicitly for every role you query against.
- **Fluree quirk:** `?s <p> ?s` does not enforce equality on this build. Use an explicit `FILTER(?s = ?o)`. `FILTER NOT EXISTS` is unaffected. (known-issues #27)
- **Never verify a FIBO term by fetching spec.edmcouncil.org** — it returns HTTP 200 for names that do not exist. Grep `sources/fibo/dev.fibo-quickstart.ttl` in subject position. Use `dev`, not `prod` — `prod` omits 40 modules.
- **The Bash tool's cwd persists between calls.** Use absolute paths; a relative write after a bare `cd` goes nowhere and a trailing `echo ok` still prints.
- Artifacts go in `sources/screening/wave18_*.json`. Tests go in `validators/test_*.py`.
- Commit after every task. Branch is `wave18-syndicated-lending`.

---

## File Structure

**Created:**

| File | Responsibility |
|---|---|
| `generators/extract_commitment_schedules.py` | Parse per-lender shares out of the six agreements' commitment schedules, with offsets |
| `generators/resolve_syndicate_institutions.py` | Resolve each lender name to a real LEI + RSSD; fetch Call Report figures |
| `generators/generate_syndicate_internal.py` | Our positions, postures, competition-law rules, projection plans, desk tracker |
| `generators/generate_disclosure_envelopes.py` | The two asymmetric bilateral envelopes |
| `generators/generate_peer_positions.py` | The peer's positions and product declarations, incl. the three engineered cases |
| `loaders/load_postgres_wave18.py` | Our Postgres slice: members, call reports, own positions, rules, projection plans |
| `loaders/load_fluree_wave18.py` | Our Fluree slice: syndicate structure, shares, agent edges, votes, envelopes |
| `loaders/load_mongo_wave18.py` | Voting-threshold and assignment passages; the SNC report |
| `loaders/load_sqlite_wave18.py` | `syndicate_desk_tracker` |
| `loaders/load_peer_wave18.py` | The peer estate, across its three stores |
| `validators/syndicate.py` | The six §F floors that counting cannot establish, recomputed live |
| `validators/test_agent_extraction.py` | Tests for the agent-identity repair |
| `validators/test_commitment_schedules.py` | Tests for the schedule parser |
| `validators/test_syndicate.py` | Tests for `validators/syndicate.py` and the loaders' invariants |

**Modified:**

| File | Change |
|---|---|
| `generators/extract_facilities.py` | Repair the `AGENT` regex (Task 1) |
| `loaders/load_facilities_wave4.py` | Re-load repaired agent values (Task 1) |
| `docs/ccf_dataprep_v2.md` | Binding table + entity tables + counts (Tasks 4, 17) |
| `validators/conditions.py` | The §F block (Task 17) |
| `validators/partition.py` | Both-direction checks (Task 17) |
| `validators/spec_coverage.py` | §C catalog rows (Task 17) |
| `docs/HANDOFF.md`, `docs/known-issues.md` | Close-out (Task 17) |

---

## Task 1: Repair administrative-agent extraction

The `AGENT` regex uses a **lazy quantifier over a character class that admits spaces and commas**, so it matches the shortest satisfying prefix rather than the institution name. On *"JPMORGAN CHASE BANK, N.A., in its capacity as administrative agent"* it captures `in its capacity`. It always matches *something*, which is why forty-five wrong values look plausible.

Repair across **all 51 syndicated facilities**, not only Wave 18's six.

**Files:**
- Modify: `generators/extract_facilities.py:90-92` (the `AGENT` regex), `:147`, `:162-165`
- Modify: `loaders/load_facilities_wave4.py` (re-load the repaired value)
- Test: `validators/test_agent_extraction.py`

**Interfaces:**
- Produces: `generators.extract_facilities.extract_agent(doc_text: str) -> dict | None` returning `{"name": str, "offset": int}` or `None`. Replaces the inline `AGENT.search` at `:147`. Task 8 reads `facility.administrative_agent` and expects an institution name resolvable against `syndicate_member.legal_name`.

- [ ] **Step 1: Write the failing test**

```python
# validators/test_agent_extraction.py
"""Task 1 — the administrative-agent repair.

Every case below is REAL TEXT taken from a filed EX-10 in sources/ex10/.
The four `corrupt` cases are the exact strings currently stored in
ccf_v2.facility.administrative_agent.
"""
import pytest
from generators.extract_facilities import extract_agent

# (agreement text fragment, expected institution name)
REAL_PREAMBLES = [
    ("JPMORGAN CHASE BANK, N.A., in its capacity as administrative agent "
     "for the Lenders", "JPMORGAN CHASE BANK, N.A."),
    ("BANK OF AMERICA, N.A., as Administrative Agent, Swing Line Lender "
     "and L/C Issuer", "BANK OF AMERICA, N.A."),
    ("GOLDMAN SACHS BANK USA, as Administrative Agent and Collateral Agent",
     "GOLDMAN SACHS BANK USA"),
    ("the several banks and other financial institutions from time to time "
     "party hereto, and BANK OF AMERICA, N.A., as Administrative Agent",
     "BANK OF AMERICA, N.A."),
    ("each lender that is a party hereto and identified on the signature "
     "pages hereof and CITIBANK, N.A., as administrative agent",
     "CITIBANK, N.A."),
    ("BARCLAYS BANK PLC, not in its individual capacity but solely as "
     "Administrative Agent", "BARCLAYS BANK PLC"),
]

@pytest.mark.parametrize("text,expected", REAL_PREAMBLES)
def test_extracts_the_institution_not_the_connective(text, expected):
    got = extract_agent(text)
    assert got is not None, f"no agent found in: {text[:60]!r}"
    assert got["name"] == expected


CONNECTIVE_FRAGMENTS = [
    "in its capacity", "in its capacities", "in such capacity",
    "that is a party hereto", "on the signature pages hereof",
    "not in its individual capacity", "and",
]

@pytest.mark.parametrize("text,expected", REAL_PREAMBLES)
def test_no_connective_survives_into_the_name(text, expected):
    """The four stored-corrupt values are all connectives. None may return."""
    got = extract_agent(text)
    lowered = got["name"].lower()
    for frag in CONNECTIVE_FRAGMENTS:
        assert lowered != frag, f"captured the connective {frag!r}"
        assert not lowered.startswith(frag + " "), f"leading {frag!r}"


def test_absent_agent_returns_none():
    """The checker must be able to say NO. A matcher that always matches
    is the defect this task exists to fix."""
    assert extract_agent("This agreement has no agent clause at all.") is None
    assert extract_agent("") is None


def test_offset_points_at_the_captured_name():
    text = "Dated as of June 4, 2014. GOLDMAN SACHS BANK USA, as Administrative Agent"
    got = extract_agent(text)
    assert text[got["offset"]:got["offset"] + len(got["name"])] == got["name"]
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run --with pytest pytest validators/test_agent_extraction.py -v`
Expected: FAIL — `ImportError: cannot import name 'extract_agent'`

- [ ] **Step 3: Implement `extract_agent`**

Replace the `AGENT` regex at `generators/extract_facilities.py:90-92` and add the function. The strategy is: find the anchor phrase, walk **backwards** over a bounded window, strip known connectives, then take the trailing institution-shaped run.

```python
#: Anchor. We search backwards from this, because the institution name
#: always PRECEDES it and a forward lazy match finds connectives instead.
AGENT_ANCHOR = re.compile(
    r",?\s*(?:not\s+in\s+its\s+individual\s+capacity\s+but\s+solely\s+)?"
    r"as\s+(?:the\s+)?administrative\s+agent", re.IGNORECASE)

#: Phrases that sit between the name and the anchor in real preambles.
#: Stripped from the RIGHT of the window before the name is taken.
AGENT_CONNECTIVES = re.compile(
    r"(?:,?\s*(?:in\s+its\s+capacit(?:y|ies)|in\s+such\s+capacity|"
    r"not\s+in\s+its\s+individual\s+capacity(?:\s+but\s+solely)?|"
    r"acting|solely)\s*)+$", re.IGNORECASE)

#: An institution name: capitalised words, allowing &, ., ',', '-', and the
#: N.A./PLC/USA style suffixes. Anchored to the END of the window.
AGENT_NAME = re.compile(
    r"([A-Z][A-Za-z&.'\-]*(?:\s+(?:of|and|the|de|von)\b)?"
    r"(?:\s+[A-Z][A-Za-z&.'\-]*)*"
    r"(?:\s*,\s*(?:N\.A\.|N\.A|PLC|Plc|S\.A\.|AG|USA|Inc\.|Ltd\.))?)\s*$")

#: Words that can never START an institution name. A window beginning with
#: one of these means we captured a fragment of the preceding clause.
AGENT_LEADING_NOISE = re.compile(
    r"^(?:and|the|each|any|such|other|its|hereto|hereof|thereto|party|"
    r"parties|lender|lenders|bank|banks|financial|institutions|from|time|"
    r"to|of|on|in|by|with|for|as|a|an)\s+", re.IGNORECASE)


def extract_agent(doc_text: str) -> dict | None:
    """The administrative agent's institution name, and its offset.

    Searches BACKWARDS from the anchor phrase. The previous forward regex
    used a lazy quantifier over a class admitting spaces and commas, so it
    matched the shortest satisfying prefix — capturing `in its capacity`
    from `JPMORGAN CHASE BANK, N.A., in its capacity as administrative
    agent`, and similar connectives on three other filings. It always
    matched something, so nothing failed loudly and forty-five facilities
    carried a wrong value that looked plausible.
    """
    anchor = AGENT_ANCHOR.search(doc_text)
    if not anchor:
        return None

    window = doc_text[max(0, anchor.start() - 120): anchor.start()]
    window = AGENT_CONNECTIVES.sub("", window).rstrip(" ,;")

    # Peel leading clause noise one word at a time until what remains
    # starts like an institution name.
    while True:
        stripped = AGENT_LEADING_NOISE.sub("", window)
        if stripped == window:
            break
        window = stripped

    m = AGENT_NAME.search(window)
    if not m:
        return None
    name = " ".join(m.group(1).split())
    if len(name) < 4:
        return None
    offset = anchor.start() - len(window) + m.start(1)
    return {"name": name, "offset": offset}
```

Then replace the call site at `:147` and the dict entry at `:162-165`:

```python
    agent = extract_agent(doc_text)
```

```python
        "administrative_agent": agent,
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `uv run --with pytest pytest validators/test_agent_extraction.py -v`
Expected: PASS — 14 tests (6 + 6 parametrised, plus 2)

- [ ] **Step 5: Re-extract and inspect the yield before loading anything**

Run: `uv run generators/extract_facilities.py`
Expected: the `administrative agent` yield line is **at least as high** as before. Then eyeball every distinct value:

```bash
uv run python -c "
import json, pathlib
d = json.loads(pathlib.Path('sources/screening/facilities_extracted.json').read_text())
names = sorted({r['administrative_agent']['name']
                for r in d['documents'] if r.get('administrative_agent')})
print(len(names), 'distinct agents'); [print(' ', n) for n in names]"
```

Every line must read as an institution. If any does not, fix the regex and repeat — do not proceed with a partial repair.

- [ ] **Step 6: Re-load, and prove the four corrupt values are gone**

Run: `uv run loaders/load_facilities_wave4.py`

```bash
uv run python -c "
from ccf.config import pg_connect, PG_SCHEMA_V2 as S
BAD = ('in its capacity', 'that is a party hereto, and BANK O',
       'and JPMORGAN CHASE BANK, N.A., in ', ' on the signature pages hereof and')
with pg_connect() as c, c.cursor() as cur:
    cur.execute(f'SELECT administrative_agent, count(*) FROM \"{S}\".facility '
                f'WHERE syndicated GROUP BY 1 ORDER BY 2 DESC')
    rows = cur.fetchall()
for name, n in rows: print(f'{n:>3}  {name!r}')
assert not [r for r in rows if r[0] in BAD], 'a corrupt value survived'
print('OK — no corrupt agent value remains')"
```

Expected: `OK — no corrupt agent value remains`

- [ ] **Step 7: Commit**

```bash
git add generators/extract_facilities.py loaders/load_facilities_wave4.py \
        validators/test_agent_extraction.py sources/screening/facilities_extracted.json
git commit -m "Wave 18 Task 1: repair administrative-agent extraction

The AGENT regex used a lazy quantifier over a class admitting spaces and
commas, so it captured the shortest satisfying prefix — 'in its capacity'
rather than the bank name. It always matched something, so nothing failed
loudly and 45 of 51 syndicated facilities carried a plausible-looking
wrong value. extract_agent() now searches backwards from the anchor,
strips connectives, and can return None."
```

---

## Task 2: Parse the commitment schedules

**Files:**
- Create: `generators/extract_commitment_schedules.py`
- Create: `sources/screening/wave18_schedules.json`
- Test: `validators/test_commitment_schedules.py`

**Interfaces:**
- Consumes: `generators.extract_facilities.TextExtractor` (HTML → text, same normalisation Wave 4 used, so offsets are comparable).
- Produces: `parse_schedule(text: str) -> list[dict]`, each `{"lender_raw": str, "amount_usd": int, "offset": int, "tranche": str}`. Artifact `sources/screening/wave18_schedules.json` shaped `{"generated_for": "wave18", "retrieved_at": "...", "agreements": [{"document": str, "facility_ids": [str], "rows": [...]}]}`. Task 3 reads `lender_raw`; Task 8 reads `amount_usd` and `offset`.

The six agreements, and their loaded facilities:

| Document | Facility IDs |
|---|---|
| `tm2511351d1_ex10-1.htm` | `FAC-6F4065`, `FAC-A4A5EE` |
| `d949183dex101.htm` | `FAC-E08688`, `FAC-105FC5`, `FAC-08F1D1`, `FAC-DFCB72` |
| `ahr-ex10_1.htm` | `FAC-405B7A`, `FAC-2A2C38` |
| `payx-ex10_1.htm` | `FAC-E386A4` |
| `d761586dex101.htm` | `FAC-E4D2F8`, `FAC-25F991`, `FAC-01BB3F`, `FAC-5F29AF` |
| `d133770dex101.htm` | `FAC-3DF1D5` |

> **Corrected 2026-08-25, ruling T2-R1.** This table originally named
> `d45696dex101.htm` (Super Micro) and `d105148dex101.htm` (Vertiv). Neither
> contains a commitment schedule — what looked like one is a letter-of-credit
> **issuing-bank sublimit table**. See `docs/wave18-design.md` §3 for the full
> reason. Do not re-add them.

- [ ] **Step 1: Write the failing test**

```python
# validators/test_commitment_schedules.py
"""Task 2 — the commitment-schedule parser.

The fixture is REAL text from sources/ex10/885590_..._d949183dex101.htm,
Schedule I, reproduced exactly as TextExtractor renders it.
"""
import pytest
from generators.extract_commitment_schedules import parse_schedule

SCHEDULE_I = (
    "Schedule I 2025 Refinancing Term Loan Commitments 2025 REFINANCING "
    "TERM LOAN LENDERS 2025 REFINANCING TERM LOAN COMMITMENTS "
    "JPMorgan Chase Bank, N.A. (as Additional 2025 Refinancing Term Loan "
    "Lender) $ 1,285,342,270.46 Cashless Option Initial Lenders (cashless "
    "roll) [on file with the Administrative Agent] $ 1,039,657,729.54 "
    "TOTAL $ 2,325,000,000.00 Third Amendment Revolving Credit Commitments "
    "THIRD AMENDMENT REVOLVING LENDER THIRD AMENDMENT REVOLVING CREDIT "
    "COMMITMENTS JPMorgan Chase Bank, N.A. $ 115,000,000.00 "
    "Barclays Bank PLC $ 97,000,000.00 "
    "Citicorp North America, Inc. $ 97,000,000.00 "
    "HSBC Bank USA, National Association $ 97,000,000.00 "
    "Wells Fargo Bank, National Association $ 97,000,000.00"
)

def test_finds_every_named_lender():
    rows = parse_schedule(SCHEDULE_I)
    names = {r["lender_raw"] for r in rows}
    assert "JPMorgan Chase Bank, N.A." in names
    assert "Barclays Bank PLC" in names
    assert "Citicorp North America, Inc." in names
    assert "HSBC Bank USA, National Association" in names
    assert "Wells Fargo Bank, National Association" in names

def test_amounts_are_cents_exact_integers():
    rows = parse_schedule(SCHEDULE_I)
    by_name = {(r["lender_raw"], r["amount_usd"]) for r in rows}
    assert ("Barclays Bank PLC", 97_000_000) in by_name
    assert ("JPMorgan Chase Bank, N.A.", 1_285_342_270) in by_name

def test_total_rows_are_not_lenders():
    """TOTAL is a sum line, not a syndicate member. Counting it would
    inflate the member population and break the sum check in Task 16."""
    rows = parse_schedule(SCHEDULE_I)
    assert not [r for r in rows if r["lender_raw"].upper().startswith("TOTAL")]

def test_placeholder_rows_are_not_lenders():
    """'Cashless Option Initial Lenders ... [on file with the
    Administrative Agent]' names no institution and must not become one."""
    rows = parse_schedule(SCHEDULE_I)
    assert not [r for r in rows if "on file with" in r["lender_raw"]]
    assert not [r for r in rows if r["lender_raw"].startswith("Cashless")]

def test_offsets_resolve_back_to_the_source_text():
    for r in parse_schedule(SCHEDULE_I):
        assert SCHEDULE_I[r["offset"]:].startswith(r["lender_raw"])

def test_text_with_no_schedule_yields_nothing():
    """The checker must be able to say NO."""
    assert parse_schedule("This agreement contains no commitment schedule.") == []
    assert parse_schedule("") == []
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run --with pytest pytest validators/test_commitment_schedules.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'generators.extract_commitment_schedules'`

- [ ] **Step 3: Implement the parser**

```python
#!/usr/bin/env python3
"""Wave 18 Task 2 — per-lender commitment shares from filed schedules.

Wave 4 parsed the FACILITY (one total commitment per row). This parses the
SCHEDULE BENEATH IT: who holds what share. §C assigns "syndicate
composition — lender names and commitments" to Fluree as `R`, so these
figures become `participatesIn` edge attributes and live in no Postgres
column — see docs/wave18-design.md §5.

Structure, not layout. A commitment schedule is a two-column table that
HTML flattens into a single run of text: an institution name followed by a
money figure. We match that shape rather than any one filer's markup — the
estate has been bitten before by a parser written against one issuer's
layout (see docs/known-issues.md, "one issuer is not the format").
"""
from __future__ import annotations

import json
import re
from datetime import date, timezone, datetime

from ccf.config import REPO_ROOT

SCREEN = REPO_ROOT / "sources" / "screening"
EX10 = REPO_ROOT / "sources" / "ex10"

#: The six selected agreements and the facilities they carry.
AGREEMENTS = [
    ("1046102_0001104659-25-031884_tm2511351d1_ex10-1.htm",
     ["FAC-6F4065", "FAC-A4A5EE"]),
    ("885590_0001193125-25-149731_d949183dex101.htm",
     ["FAC-E08688", "FAC-105FC5", "FAC-08F1D1", "FAC-DFCB72"]),
    ("1632970_0001193125-26-145647_ahr-ex10_1.htm",
     ["FAC-405B7A", "FAC-2A2C38"]),
    ("1375365_0001193125-26-269703_d45696dex101.htm", ["FAC-517638"]),
    ("1674101_0001193125-26-088484_d105148dex101.htm", ["FAC-BEDC52"]),
    ("723531_0001193125-26-021794_payx-ex10_1.htm", ["FAC-E386A4"]),
]

#: An institution name immediately followed by a money figure. The name
#: must start capitalised and may carry a parenthetical role note, which is
#: dropped. Money is >= $1,000,000 — schedules never list less, and the
#: floor keeps section numbers and dates out.
SCHEDULE_ROW = re.compile(
    r"(?P<name>[A-Z][A-Za-z0-9&.,'\-]*(?:\s+[A-Z0-9][A-Za-z0-9&.,'\-]*)*)"
    r"(?:\s*\([^)]{0,80}\))?"
    r"(?:\s*\[[^\]]{0,80}\])?"
    r"\s*\$\s?(?P<amount>[\d,]{9,}(?:\.\d\d)?)")

#: Lines that are sums, placeholders or headings — never syndicate members.
NOT_A_LENDER = re.compile(
    r"^(?:TOTAL|AGGREGATE|SUB-?TOTAL|Cashless|Schedule|Annex|Exhibit|"
    r"Commitment|Commitments|Lender|Lenders|Revolving|Term)\b", re.IGNORECASE)


def parse_schedule(text: str) -> list[dict]:
    """Every (lender, amount, offset) pair a commitment schedule states."""
    rows: list[dict] = []
    for m in SCHEDULE_ROW.finditer(text):
        name = " ".join(m.group("name").split()).strip(" ,")
        if NOT_A_LENDER.match(name):
            continue
        if "on file with" in m.group(0).lower():
            continue
        if len(name) < 6:
            continue
        amount = int(float(m.group("amount").replace(",", "")))
        if amount < 1_000_000:
            continue
        rows.append({
            "lender_raw": name,
            "amount_usd": amount,
            "offset": m.start("name"),
            "tranche": _tranche_for(text, m.start()),
        })
    return rows


#: Tranche headings that precede a block of rows. The nearest preceding
#: heading labels the block — a schedule commonly lists a term-loan block
#: and a revolver block under one Schedule I.
TRANCHE_HEADING = re.compile(
    r"((?:[A-Z][A-Za-z0-9]*\s+){0,5}"
    r"(?:Term\s+Loan|Revolving\s+Credit|Revolving|Delayed\s+Draw)"
    r"(?:\s+[A-Za-z]+){0,3}\s+Commitments?)", re.IGNORECASE)


def _tranche_for(text: str, pos: int) -> str:
    """The nearest tranche heading at or before `pos`, or 'unspecified'."""
    best = "unspecified"
    for m in TRANCHE_HEADING.finditer(text, 0, pos):
        best = " ".join(m.group(1).split())
    return best


def main() -> int:
    from generators.extract_facilities import TextExtractor

    out = []
    for filename, facility_ids in AGREEMENTS:
        path = EX10 / filename
        if not path.exists():
            raise SystemExit(f"missing source document: {path}")
        parser = TextExtractor()
        parser.feed(path.read_text(errors="ignore"))
        parser.close()
        rows = parse_schedule(parser.text())
        if not rows:
            raise SystemExit(
                f"{filename}: zero schedule rows parsed. This filing was "
                f"selected BECAUSE it carries a schedule — an empty parse "
                f"is a parser defect, not an empty document.")
        out.append({
            "document": filename,
            "facility_ids": facility_ids,
            "rows": rows,
        })
        names = sorted({r["lender_raw"] for r in rows})
        print(f"  {filename[:44]:46s} {len(rows):>3} rows  "
              f"{len(names):>2} lenders")

    artifact = {
        "generated_for": "wave18 · syndicated-lending-co-lender",
        "method": "structural parse of filed commitment schedules",
        "provenance": "public",
        "source": "SEC EDGAR EX-10 commitment schedules",
        "retrieved_at": datetime.now(timezone.utc).date().isoformat(),
        "agreements": out,
    }
    (SCREEN / "wave18_schedules.json").write_text(
        json.dumps(artifact, indent=2))
    total = sum(len(a["rows"]) for a in out)
    lenders = sorted({r["lender_raw"] for a in out for r in a["rows"]})
    print(f"\n  {total} schedule rows across {len(out)} agreements, "
          f"{len(lenders)} distinct lender names")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `uv run --with pytest pytest validators/test_commitment_schedules.py -v`
Expected: PASS — 6 tests

- [ ] **Step 5: Generate the artifact and read the lender list**

Run: `uv run generators/extract_commitment_schedules.py`

Expected: six lines, then a distinct-lender count. **Read the names.** If fewer than 20 distinct lenders appear, or any name is a heading fragment, the regex needs work — §F needs ~25 institutions and a padded list is worse than a short one.

- [ ] **Step 6: Commit**

```bash
git add generators/extract_commitment_schedules.py \
        validators/test_commitment_schedules.py \
        sources/screening/wave18_schedules.json
git commit -m "Wave 18 Task 2: parse per-lender commitment shares

Six filed agreements, structural parse rather than per-issuer layout.
TOTAL lines and '[on file with the Administrative Agent]' placeholders
are excluded — both would otherwise become syndicate members and break
the share-sum check."
```

---

## Task 3: Resolve institutions to real LEI and RSSD

**Files:**
- Create: `generators/resolve_syndicate_institutions.py`
- Create: `sources/screening/wave18_institutions.json`
- Test: `validators/test_syndicate.py` (first block)

**Interfaces:**
- Consumes: `sources/screening/wave18_schedules.json` (`lender_raw`).
- Produces: artifact rows `{"member_id": str, "legal_name": str, "lei": str, "rssd": str|None, "raw_names": [str], "provenance": "public", "source": str, "retrieved_at": str}` plus `call_reports: [{"rssd", "report_date", "tier1_capital", "total_assets", ...}]`. `member_id` is `SYNM-<8 hex of sha256(lei)>` — **content-keyed, never positional**. Task 5 loads both lists.

- [ ] **Step 1: Write the failing test**

```python
# validators/test_syndicate.py
"""Wave 18 — syndicate data invariants and the §F floors."""
import hashlib
import json
import re
import pytest

from ccf.config import REPO_ROOT

SCREEN = REPO_ROOT / "sources" / "screening"

def _institutions():
    path = SCREEN / "wave18_institutions.json"
    if not path.exists():
        pytest.skip("Task 3 has not run yet")
    return json.loads(path.read_text())

LEI_RE = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")

def test_every_member_carries_a_real_gleif_lei():
    """Real LEIs are 20 alphanumerics with no hyphen. The SYN- synthetic
    format must never appear here — these are real institutions."""
    for m in _institutions()["members"]:
        assert LEI_RE.match(m["lei"]), f"{m['legal_name']}: {m['lei']!r}"
        assert not m["lei"].startswith("SYN-"), (
            f"{m['legal_name']} carries a synthetic LEI; §F requires real ones")

def test_member_ids_are_content_keyed_not_positional():
    """Four loaders on main already rewrite other waves' rows when a table
    grows. A positional id would do the same here."""
    for m in _institutions()["members"]:
        digest = hashlib.sha256(m["lei"].encode()).hexdigest()[:8]
        assert m["member_id"] == f"SYNM-{digest}", (
            f"{m['legal_name']}: id is not derived from its LEI")

def test_member_ids_are_unique():
    ids = [m["member_id"] for m in _institutions()["members"]]
    assert len(ids) == len(set(ids))

def test_at_least_twenty_five_institutions():
    """§F: ~25 syndicate member institutions."""
    assert len(_institutions()["members"]) >= 25

def test_our_bank_and_the_peer_are_both_present():
    """The whole product rests on JPMorgan and Bank of America sitting in
    the same syndicates. If either is missing the demonstration is moot."""
    leis = {m["lei"] for m in _institutions()["members"]}
    assert "7H6GLXDRUGQFU57RNE97" in leis, "JPMorgan Chase Bank NA absent"
    names = " | ".join(m["legal_name"] for m in _institutions()["members"])
    assert "BANK OF AMERICA" in names.upper()

def test_raw_names_map_back_to_the_schedules():
    """Every lender_raw the parser found must resolve to exactly one
    member, or a commitment edge in Task 8 will have no member to attach to."""
    schedules = json.loads((SCREEN / "wave18_schedules.json").read_text())
    raw_seen = {r["lender_raw"] for a in schedules["agreements"]
                for r in a["rows"]}
    mapped = {n for m in _institutions()["members"] for n in m["raw_names"]}
    assert raw_seen <= mapped, f"unmapped lender names: {sorted(raw_seen - mapped)}"
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run --with pytest pytest validators/test_syndicate.py -v`
Expected: all tests SKIP (`Task 3 has not run yet`) — this is the correct pre-state.

- [ ] **Step 3: Implement the resolver**

Read `generators/fetch_reporting_bank.py` first — it already fetches FDIC BankFind and GLEIF for one bank and is the pattern to reuse. Key points for the new module:

```python
#!/usr/bin/env python3
"""Wave 18 Task 3 — schedule lender names -> real LEI and RSSD.

§C: "Co-lender institution identities | FFIEC NIC RSSD; GLEIF LEI | public
| Postgres". Filed schedules name institutions in a dozen spellings
("JPMorgan Chase Bank, N.A." / "JPMORGAN CHASE BANK, N.A." /
"JPMorgan Chase Bank, National Association"); all must collapse to ONE
member carrying ONE real LEI, or Task 8's edges attach to phantom members.

member_id is sha256(lei)[:8], NOT a row index. See CLAUDE.md and
docs/known-issues.md on positional identity.
"""
```

- `normalise(name: str) -> str` — uppercase, drop punctuation, expand `N.A.` ↔ `NATIONAL ASSOCIATION`, drop parenthetical role notes.
- `resolve(names: list[str]) -> list[dict]` — group by `normalise`, then query GLEIF `https://api.gleif.org/api/v1/lei-records?filter[entity.legalName]=<name>` and FDIC BankFind `https://banks.data.fdic.gov/api/institutions?filters=NAME:"<name>"` for `RSSD`/`CERT`.
- Any name that resolves to **zero or more than one** LEI must be written to a `manual_review` list in the artifact and **printed loudly**, not silently guessed. Resolve those by hand against gleif.org and add a `MANUAL_LEI` mapping table in the module, with the retrieval date beside each.
- `member_id = "SYNM-" + hashlib.sha256(lei.encode()).hexdigest()[:8]`.
- Fetch Call Report figures for each resolved RSSD (`tier1_capital`, `total_assets`, `total_equity`, `report_date`) exactly as `fetch_reporting_bank.py` does.

- [ ] **Step 4: Run it, and resolve every manual-review name before proceeding**

Run: `uv run generators/resolve_syndicate_institutions.py`

Expected: a resolved count, then an explicit `MANUAL REVIEW` block if any name is ambiguous. **The task is not done while that block is non-empty** — an unresolved institution becomes a member with no LEI, which fails Task 16's floor.

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `uv run --with pytest pytest validators/test_syndicate.py -v`
Expected: PASS — 6 tests

- [ ] **Step 6: Commit**

```bash
git add generators/resolve_syndicate_institutions.py \
        sources/screening/wave18_institutions.json validators/test_syndicate.py
git commit -m "Wave 18 Task 3: resolve schedule lenders to real LEI and RSSD

Name variants collapse to one member per institution. member_id is
sha256(lei)[:8] — content-keyed, so a growing table cannot rewrite
another wave's rows. Ambiguous names go to manual review rather than
being guessed."
```

---

## Task 4: Verify and bind the FIBO terms

**Files:**
- Create: `generators/verify_fibo_wave18.py`
- Modify: `docs/ccf_dataprep_v2.md` (binding table)
- Send: a bundle to `~/.agent-exchange/ccf-dataprep/outbox/`

**Interfaces:**
- Produces: the module-level IRI constants Tasks 8–10 and 14–16 import. Name them in `ccf/config.py` or a new `ccf/syndicate.py` so loader and validator share **one** definition — a validator holding its own copy of a wrong constant agrees with itself and cannot detect the defect (see `conditions.py`'s Wave 8 correction note).

- [ ] **Step 1: Confirm what FIBO already has**

```bash
F=sources/fibo/dev.fibo-quickstart.ttl
for t in SyndicatedLoan FinanceSyndicate FinanceSyndicateMember \
         AdministrativeAgent LeadArranger Bookrunner SyndicationAgent; do
  printf '%-26s ' "$t"; grep -c "^fibo-sec-dbt-dln:$t$" "$F"
done
grep -n "@prefix fibo-sec-dbt-dln\|@prefix fibo-fnd-agr-agr\|@prefix cmns-col" "$F"
```

Expected: each class present; the `fibo-sec-dbt-dln` prefix resolving to `https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/DistributedLoans/`.

- [ ] **Step 2: Write the term-verification script**

Model it on `generators/verify_fibo_wave8.py` and `generators/verify_fibo_terms.py`, which already do exactly this. It must, for every term Wave 18 uses:
- assert the IRI appears **in subject position** in `dev.fibo-quickstart.ttl` (a `rdf:about`/subject match — not a substring anywhere in the file);
- for object properties, print `rdfs:domain` and `rdfs:range` so a wrong-semantics reuse is visible;
- exit non-zero if any claimed-FIBO term is absent.

- [ ] **Step 3: Run it and read the domains and ranges**

Run: `uv run generators/verify_fibo_wave18.py`

**Two known traps, already established — do not re-derive them:**
- `fibo-loan-ln-reg:administeredBy` has `rdfs:domain fibo-loan-ln-reg:LoanRegulatoryRequirement` and `rdfs:range cmns-rga:RegulatoryAgency`. It is about a regulator overseeing a rule. **It is not our administered-by.** Mint `ex:administeredBy` instead, or find a FIBO property whose domain admits a credit facility.
- `SyndicateMember` resolves to `fibo-be-fct-fct:SyndicateMember` (generic) and `fibo-bp-iss-ipo:SyndicateMember` (IPO underwriting). Use `fibo-sec-dbt-dln:FinanceSyndicateMember`.

- [ ] **Step 4: Decide `participatesIn`, and record the reasoning**

`fibo-sec-dbt-dln:FinanceSyndicateMember`'s own restriction uses `cmns-rlcmp:isPlayedBy` over `cmns-col:isMemberOf` with `allValuesFrom fibo-sec-dbt-dln:FinanceSyndicate`. If `cmns-col:isMemberOf` is present in the ontology with a compatible domain, use it and mint nothing. If not, mint `ex:participatesIn`. Either way, **write the decision and its evidence into `docs/ccf_dataprep_v2.md`**, not into a commit message — the vault mirror and the SDK project read the doc.

- [ ] **Step 5: Add every term to the binding table**

Edit `docs/ccf_dataprep_v2.md`'s Canonical FIBO IRI binding section. Full IRIs, one row each, for: `SyndicatedLoan`, `FinanceSyndicate`, `FinanceSyndicateMember`, `AdministrativeAgent`, `Commitment`, the membership property chosen in Step 4, plus every `ex:` term minted here — at minimum `ex:votesOn`, `ex:sharesCollateralWith`, `ex:DisclosureEnvelope`, `ex:requestScope`, `ex:discloseScope`, `ex:declaredTtlSeconds`, `ex:attestation`, `ex:declaredLatencyMs`, `ex:disclosurePrecision`.

Verify the backticks survived the write — markdown code spans have been silently eaten by heredocs twice in this repo:

```bash
grep -c '`' docs/ccf_dataprep_v2.md
grep -n "DistributedLoans" docs/ccf_dataprep_v2.md | head
```

- [ ] **Step 6: Send the corrected mirror through the exchange**

Read **section 5 of the `obsidian-vault-access` skill** before the first send. The message directory is `~/.agent-exchange/ccf-dataprep/outbox/<YYYY-MM-DDTHH-MM-SSZ>-<slug>` — **hyphens in the time, never colons**, or the vault's reconciler rejects it visibly but unsent. Never edit a previously published bundle; a correction is a new bundle naming what it supersedes.

- [ ] **Step 7: Commit, and say so in your response**

```bash
git add docs/ccf_dataprep_v2.md generators/verify_fibo_wave18.py
git commit -m "Wave 18 Task 4: bind FIBO DistributedLoans terms

SyndicatedLoan, FinanceSyndicate, FinanceSyndicateMember and
AdministrativeAgent all exist in FIBO and are bound rather than invented.
Records two traps: fibo-loan-ln-reg:administeredBy is regulator-scoped
(domain LoanRegulatoryRequirement, range RegulatoryAgency) and wrong for
us; SyndicateMember resolves to two unrelated FIBO terms, neither the
lending one."
```

**Your response for this task MUST name the terms added and state that the vault mirror needs refreshing, and that you have sent it.** CLAUDE.md, "Definition of done", item 5.

---

## Task 5: Postgres DDL, members and call reports

**Files:**
- Create: `loaders/load_postgres_wave18.py`
- Test: `validators/test_syndicate.py` (append)

**Interfaces:**
- Consumes: `sources/screening/wave18_institutions.json`.
- Produces: `ccf_v2.syndicate_member`, `ccf_v2.member_call_report`; functions `load_members(cur, members) -> int`, `load_call_reports(cur, reports) -> int`. Tasks 6 and 7 extend this same module and its `DDL` constant.

- [ ] **Step 1: Write the failing test**

```python
# append to validators/test_syndicate.py
from ccf.config import pg_connect, PG_SCHEMA_V2 as S

def _pg(sql, params=None):
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()

def test_syndicate_member_table_is_populated():
    n = _pg(f'SELECT count(*) FROM "{S}".syndicate_member')[0][0]
    assert n >= 25

def test_no_member_carries_a_commitment_amount():
    """§C assigns commitments to FLUREE. A commitment column in Postgres is
    a single-writer violation, and the design records that an earlier draft
    made exactly this mistake."""
    cols = {r[0] for r in _pg(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema=%s AND table_name='syndicate_member'", (S,))}
    forbidden = {c for c in cols
                 if "commitment" in c or "share" in c or "envelope" in c}
    assert not forbidden, f"Fluree-owned attributes in Postgres: {forbidden}"

def test_no_member_was_inserted_into_the_crosswalk():
    """PREFLIGHT RULING P1. An earlier draft of this plan required a
    crosswalk row per member. That would violate
    conditions.py's CROSSWALK_INVARIANTS["crosswalk rows pointing at no
    entity"], which requires every crosswalk row to have a legal_entity
    row by LEI — and these banks are not in legal_entity. Syndicate
    members are counterparty institutions, not clients: they have no
    internal_client_id, and §C names this product's correlation key as
    facility_id plus lender LEI and RSSD. The correct state is ZERO
    crosswalk rows for them, asserted so nobody re-adds them."""
    leaked = _pg(f'SELECT m.lei FROM "{S}".syndicate_member m '
                 f'JOIN "{S}".crosswalk x ON x.lei = m.lei')
    assert not leaked, (
        f"syndicate members inserted into the crosswalk: {leaked} — this "
        f"breaks CROSSWALK_INVARIANTS estate-wide")

def test_the_crosswalk_invariants_still_hold():
    """The check that would actually catch a violation, run directly."""
    from validators.conditions import CROSSWALK_INVARIANTS
    for name, sql in CROSSWALK_INVARIANTS.items():
        assert _pg(sql)[0][0] == 0, f"invariant violated: {name}"

def test_call_reports_reference_a_real_member():
    orphans = _pg(f'SELECT r.rssd FROM "{S}".member_call_report r '
                  f'LEFT JOIN "{S}".syndicate_member m ON m.rssd = r.rssd '
                  f'WHERE m.rssd IS NULL')
    assert not orphans, f"call reports for unknown institutions: {orphans}"
```

- [ ] **Step 2: Run and confirm it fails**

Run: `uv run --with pytest pytest validators/test_syndicate.py -k "member or call_report" -v`
Expected: FAIL — `psycopg.errors.UndefinedTable: relation "ccf_v2.syndicate_member" does not exist`

- [ ] **Step 3: Write the loader**

Copy the module shape from `loaders/load_postgres_wave17.py` — a `DDL` string constant, one `load_*` function per table, a `main()` that calls `assert_v2_schema(S)` then `cur.execute(DDL)`.

```python
DDL = f'''
CREATE TABLE IF NOT EXISTS "{S}".syndicate_member (
    member_id       TEXT PRIMARY KEY,
    legal_name      TEXT NOT NULL,
    -- NULLABLE, corrected 2026-08-26 against the real Task 3 artifact.
    -- Five members are credit funds with no GLEIF registration at all
    -- (ruling T3-R1); they are real firms named in a real filing, so they
    -- are neither dropped nor given a SYN- identifier. An earlier draft of
    -- this DDL said NOT NULL and would have failed on insert.
    -- UNIQUE still holds: PostgreSQL permits many NULLs under a UNIQUE
    -- constraint, so it constrains the 40 real LEIs and ignores the rest.
    lei             TEXT NULL UNIQUE,
    rssd            TEXT NULL,
    -- Which field member_id was derived from: 'lei' or 'legal_name'.
    id_basis        TEXT NOT NULL,
    -- GLEIF entity.category. Recorded so the BRANCH-vs-GENERAL defect that
    -- bound Bank of America and Citibank to Jakarta branch registrations
    -- stays detectable rather than being fixed once and forgotten.
    gleif_category  TEXT NULL,
    raw_names       JSONB NOT NULL,
    provenance      TEXT NOT NULL,
    source          TEXT NOT NULL,
    retrieved_at    DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".member_call_report (
    rssd                TEXT NOT NULL,
    report_date         DATE NOT NULL,
    tier1_capital       NUMERIC NULL,
    total_assets        NUMERIC NULL,
    total_equity        NUMERIC NULL,
    provenance          TEXT NOT NULL,
    source              TEXT NOT NULL,
    PRIMARY KEY (rssd, report_date)
);
'''
```

```python
def load_members(cur, members: list[dict]) -> int:
    rows = [(m["member_id"], m["legal_name"], m["lei"], m.get("rssd"),
             json.dumps(m["raw_names"]), m["provenance"], m["source"],
             m["retrieved_at"]) for m in members]
    cur.executemany(
        f'INSERT INTO "{S}".syndicate_member '
        "(member_id, legal_name, lei, rssd, raw_names, provenance, source, "
        " retrieved_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (member_id) DO UPDATE SET "
        "legal_name=EXCLUDED.legal_name, lei=EXCLUDED.lei, "
        "rssd=EXCLUDED.rssd, raw_names=EXCLUDED.raw_names, "
        "provenance=EXCLUDED.provenance, source=EXCLUDED.source, "
        "retrieved_at=EXCLUDED.retrieved_at",
        rows)
    return len(rows)
```

`load_call_reports` follows the same shape with `ON CONFLICT (rssd, report_date)`.

**Do NOT add crosswalk rows** — preflight ruling P1. `ccf_v2.crosswalk` is keyed `internal_client_id` with a `UNIQUE (lei)`, and `conditions.py`'s `CROSSWALK_INVARIANTS["crosswalk rows pointing at no entity"]` requires every crosswalk row to join to `legal_entity` by LEI. These banks are not in `legal_entity`, so inserting them would put the estate-wide condition register red. They are counterparties, not clients.

- [ ] **Step 4: Run the loader**

Run: `uv run loaders/load_postgres_wave18.py`
Expected: `loaded: syndicate_member NN, member_call_report NN`

- [ ] **Step 5: Prove idempotency by VALUE, not by count**

A count cannot see a field being reset. Name a value:

```bash
uv run python -c "
from ccf.config import pg_connect, PG_SCHEMA_V2 as S
q = f'SELECT member_id, legal_name, rssd FROM \"{S}\".syndicate_member ORDER BY member_id'
with pg_connect() as c, c.cursor() as cur:
    cur.execute(q); before = cur.fetchall()
import subprocess; subprocess.run(['uv','run','loaders/load_postgres_wave18.py'], check=True)
with pg_connect() as c, c.cursor() as cur:
    cur.execute(q); after = cur.fetchall()
assert before == after, 'a re-run changed row content'
print(f'OK — {len(after)} rows identical across a re-run')"
```

- [ ] **Step 6: Run the tests and commit**

Run: `uv run --with pytest pytest validators/test_syndicate.py -v`

```bash
git add loaders/load_postgres_wave18.py validators/test_syndicate.py
git commit -m "Wave 18 Task 5: syndicate_member and member_call_report

Institution identity and financial condition only. Commitment shares and
disclosure envelopes are Fluree-owned per §C and are deliberately absent
from these tables — a test asserts no commitment/share/envelope column
exists here."
```

---

## Task 6: Our positions, ratings and workout postures

**Files:**
- Create: `generators/generate_syndicate_internal.py`
- Create: `sources/screening/wave18_internal.json`
- Modify: `loaders/load_postgres_wave18.py` (add `own_position`, `competition_law_rule`)
- Test: `validators/test_syndicate.py` (append)

**Interfaces:**
- Produces: `ccf_v2.own_position` keyed `(facility_id, member_id)`; `ccf_v2.competition_law_rule` keyed `rule_id`. `load_own_positions(cur, rows) -> int`, `load_competition_rules(cur, rows) -> int`.

- [ ] **Step 1: Write the failing test**

```python
# append to validators/test_syndicate.py
def test_our_position_exists_on_every_selected_facility():
    n = _pg(f'SELECT count(DISTINCT facility_id) FROM "{S}".own_position')[0][0]
    assert n >= 6

def test_our_positions_are_labelled_synthetic_internal():
    bad = _pg(f'SELECT DISTINCT provenance FROM "{S}".own_position '
              f"WHERE provenance <> 'synthetic — internal'")
    assert not bad, f"wrong provenance labels: {bad}"

def test_our_share_never_exceeds_the_facility_commitment():
    over = _pg(f'SELECT p.facility_id, p.share_usd, f.commitment_amount '
               f'FROM "{S}".own_position p '
               f'JOIN "{S}".facility f USING (facility_id) '
               f'WHERE p.share_usd > f.commitment_amount')
    assert not over, f"our share exceeds the whole facility: {over}"

def test_workout_posture_is_from_a_closed_vocabulary():
    allowed = {"performing", "watch", "workout", "restructuring", "exit"}
    got = {r[0] for r in _pg(f'SELECT DISTINCT workout_posture FROM "{S}".own_position')}
    assert got <= allowed, f"unexpected postures: {got - allowed}"

def test_competition_law_rules_exist_and_are_internal():
    rows = _pg(f'SELECT count(*), count(*) FILTER '
               f"(WHERE provenance = 'synthetic — internal') "
               f'FROM "{S}".competition_law_rule')
    total, internal = rows[0]
    assert total >= 3 and total == internal
```

- [ ] **Step 2: Run and confirm it fails**

Run: `uv run --with pytest pytest validators/test_syndicate.py -k "position or competition" -v`
Expected: FAIL — `relation "ccf_v2.own_position" does not exist`

- [ ] **Step 3: Extend the DDL and write the generator**

```python
DDL_INTERNAL = f'''
CREATE TABLE IF NOT EXISTS "{S}".own_position (
    facility_id       TEXT NOT NULL,
    member_id         TEXT NOT NULL,
    share_usd         NUMERIC NOT NULL,
    internal_rating   TEXT NOT NULL,
    workout_posture   TEXT NOT NULL,
    as_of             DATE NOT NULL,
    provenance        TEXT NOT NULL,
    PRIMARY KEY (facility_id, member_id)
);

CREATE TABLE IF NOT EXISTS "{S}".competition_law_rule (
    rule_id       TEXT PRIMARY KEY,
    jurisdiction  TEXT NOT NULL,
    constrains    TEXT NOT NULL,
    rule_text     TEXT NOT NULL,
    provenance    TEXT NOT NULL
);
'''
```

The generator writes `sources/screening/wave18_internal.json`.

**PREFLIGHT RULING T6-R1, measured 2026-08-26.** JPMorgan is a filed lender on **7 of the 14 facilities** — RB Global (2), Bausch (4), Paychex (1) — and is absent from AHR (2), Regis (4) and Sabre (1).

- Where the filing names us, `share_usd` **is the filed figure**, verbatim. Inventing a different number would contradict a public document.
- Where the filing does **not** name us, record **no position at all**. Do not invent one. Those schedules name a complete lender list whose shares already sum to the facility total; inserting a JPMorgan share would contradict the filing and break Task 16's share-reconciliation floor.

An earlier draft of this step said to invent a share where the schedule does not name us. That was written before the coverage was measured. 7 ≥ 6, so the floor below is met from filed facts alone.

**This is a feature, not a shortfall.** The seven facilities where we hold no position are exactly what the `prospective` perspective (Task 7) is for — a participant evaluating a syndicate it has not joined. The product gains a real population for that perspective instead of a synthetic one.

`internal_rating` and `workout_posture` are ours to invent and are labelled `synthetic — internal`; they attach only to the seven positions we actually hold.

Ratings come from the existing `ccf_v2.rating_scale` table — read it rather than inventing a scale.

At least three competition-law rules, e.g. constraining forward-looking pricing exchange, constraining disclosure of another borrower's terms, constraining exchange of unannounced workout intent.

- [ ] **Step 4: Generate, load, run tests**

```bash
uv run generators/generate_syndicate_internal.py
uv run loaders/load_postgres_wave18.py
uv run --with pytest pytest validators/test_syndicate.py -v
```

- [ ] **Step 5: Commit**

```bash
git add generators/generate_syndicate_internal.py \
        sources/screening/wave18_internal.json \
        loaders/load_postgres_wave18.py validators/test_syndicate.py
git commit -m "Wave 18 Task 6: own positions, ratings and workout postures

Where a filed schedule names JPMorgan, our share is that filed figure —
inventing a different number would contradict a public document."
```

---

## Task 7: Projection plans per perspective

**Files:**
- Modify: `generators/generate_syndicate_internal.py`, `loaders/load_postgres_wave18.py`
- Test: `validators/test_syndicate.py` (append)

**Interfaces:**
- Produces: `ccf_v2.syndicate_projection_plan (perspective TEXT PRIMARY KEY, elements JSONB NOT NULL, provenance TEXT NOT NULL)`; `load_projection_plans(cur, plans) -> int`.

A **new table**, not a widening of Wave 7's `projection_plan` or Wave 16's `ib_projection_plan` — both encode a different product's vocabulary, and this one keys on `perspective`. Wave 16 and Wave 17 both set this precedent.

- [ ] **Step 1: Write the failing test**

```python
# append to validators/test_syndicate.py
def test_three_perspectives_exist():
    got = {r[0] for r in _pg(
        f'SELECT perspective FROM "{S}".syndicate_projection_plan')}
    assert got == {"agent", "participant", "prospective"}

def test_the_three_plans_assemble_different_element_sets():
    """§D: the agent's perspective carries documentation and waterfall
    detail no participant receives; a prospective participant receives
    materially less than an existing one. Three identical plans would make
    the perspective parameter decorative."""
    rows = dict(_pg(f'SELECT perspective, elements FROM '
                    f'"{S}".syndicate_projection_plan'))
    sets = {k: set(v) for k, v in rows.items()}
    assert sets["agent"] != sets["participant"]
    assert sets["participant"] != sets["prospective"]
    assert sets["prospective"] < sets["participant"] < sets["agent"], (
        "the three must nest: prospective ⊂ participant ⊂ agent")
```

- [ ] **Step 2: Run and confirm it fails**

Run: `uv run --with pytest pytest validators/test_syndicate.py -k perspective -v`
Expected: FAIL — `relation "ccf_v2.syndicate_projection_plan" does not exist`

- [ ] **Step 3: Add the DDL, generate the three plans, load them**

The element names must be things that actually exist in the estate, so Task 16 can assemble them. Suggested, adjust to what you built:

```python
PLANS = {
    "agent": ["syndicate_composition", "member_commitment", "own_position",
              "administrative_agent", "voting_thresholds", "assignment_terms",
              "amendment_vote_posture", "payment_waterfall", "desk_tracker_note",
              "peer_position", "divergence_indicator"],
    "participant": ["syndicate_composition", "member_commitment",
                    "own_position", "administrative_agent",
                    "voting_thresholds", "amendment_vote_posture",
                    "peer_position", "divergence_indicator"],
    "prospective": ["syndicate_composition", "administrative_agent",
                    "voting_thresholds"],
}
```

- [ ] **Step 4: Run the tests and commit**

```bash
uv run loaders/load_postgres_wave18.py
uv run --with pytest pytest validators/test_syndicate.py -v
git add generators/generate_syndicate_internal.py loaders/load_postgres_wave18.py \
        sources/screening/wave18_internal.json validators/test_syndicate.py
git commit -m "Wave 18 Task 7: three projection plans, strictly nested

Own table rather than widening Wave 7's projection_plan or Wave 16's
ib_projection_plan — both key on a different product's vocabulary."
```

---

## Task 8: Fluree — syndicate structure and commitment shares

**Files:**
- Create: `loaders/load_fluree_wave18.py`
- Test: `validators/test_syndicate.py` (append)

**Interfaces:**
- Consumes: `wave18_schedules.json`, `wave18_institutions.json`, `ccf_v2.facility`.
- Produces: Fluree nodes and edges in ledger `FLUREE_LEDGER_V2`. `load_structure() -> dict` returning counts. Task 9 and 10 extend this module.

**Node discipline:** a `FinanceSyndicateMember` node carries `lei`, `rdfs:label`, and its types — **nothing else**. Every other attribute resolves from Postgres. Fluree runs without inference, so type each node explicitly for every role queried against.

- [ ] **Step 1: Write the failing test**

```python
# append to validators/test_syndicate.py
from ccf import fluree
from ccf.config import FLUREE_LEDGER_V2 as L

DLN = "https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/DistributedLoans/"
EX = "http://example.org/fibo/"

def _n(sparql):
    rows = fluree.query(sparql)["results"]["bindings"]
    return int(rows[0]["n"]["value"]) if rows else 0

def test_syndicated_loan_nodes_exist():
    assert _n(f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{L}> "
              f"WHERE {{ ?s a <{DLN}SyndicatedLoan> }}") >= 6

def test_member_nodes_are_explicitly_typed():
    """No OWL inference here — a query for FinanceSyndicateMember returns
    only nodes explicitly typed as one."""
    assert _n(f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{L}> "
              f"WHERE {{ ?s a <{DLN}FinanceSyndicateMember> }}") >= 25

def test_member_nodes_carry_no_postgres_owned_attribute():
    """Single-writer discipline: nodes carry lei + label and nothing else."""
    forbidden = ["legalName", "rssd", "tier1Capital", "totalAssets",
                 "internalRating", "workoutPosture"]
    for attr in forbidden:
        n = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
               f"?s a <{DLN}FinanceSyndicateMember> ; <{EX}{attr}> ?v }}")
        assert n == 0, f"{attr} is duplicated into Fluree; Postgres owns it"

def test_commitment_shares_live_on_the_edges():
    """§C assigns commitments to Fluree as R. If the share is not here,
    it is nowhere — the design forbids a Postgres copy."""
    assert _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
              f"?e <{EX}commitmentUsd> ?v }}") >= 25

def test_every_commitment_edge_cites_a_passage():
    """A public figure with no offset back to the filing is unverifiable."""
    n_edges = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                 f"?e <{EX}commitmentUsd> ?v }}")
    n_cited = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                 f"?e <{EX}commitmentUsd> ?v ; <{EX}sourcePassage> ?p }}")
    assert n_edges == n_cited, f"{n_edges - n_cited} shares cite no passage"
```

- [ ] **Step 2: Run and confirm it fails**

Run: `uv run --with pytest pytest validators/test_syndicate.py -k "syndicated_loan or member_nodes or commitment" -v`
Expected: FAIL — counts are 0.

- [ ] **Step 3: Write the loader**

Copy the SPARQL-update shape from an existing Fluree loader (`loaders/load_fluree_wave17.py` or whichever Wave 17 used). Key points:

- `fluree.update(...)` guards the ledger; never pass a literal.
- Instance URIs: `http://example.org/fibo/syndicate/<facility_id>`, `.../member/<member_id>`, `.../participation/<facility_id>-<member_id>`. **Content-keyed.**
- Type each member node as **both** `fibo-sec-dbt-dln:FinanceSyndicateMember` and whatever role queries need (`AdministrativeAgent` where it is the agent).
- The share edge is reified: a `participation` node carrying `ex:commitmentUsd`, `ex:sourcePassage`, and links to member and syndicate. A plain triple cannot carry the offset.
- Idempotency: `DELETE { ... } INSERT { ... } WHERE` on the node's own subject, so a re-run replaces rather than accumulates.

- [ ] **Step 4: Load, then verify the counts by query, not by the loader's own report**

```bash
uv run loaders/load_fluree_wave18.py
uv run --with pytest pytest validators/test_syndicate.py -v
```

- [ ] **Step 5: Prove idempotency by value**

```bash
uv run python -c "
from ccf import fluree
from ccf.config import FLUREE_LEDGER_V2 as L
EX='http://example.org/fibo/'
q=(f'SELECT ?e ?v FROM <{L}> WHERE {{ ?e <{EX}commitmentUsd> ?v }} ORDER BY ?e')
before=fluree.query(q)['results']['bindings']
import subprocess; subprocess.run(['uv','run','loaders/load_fluree_wave18.py'],check=True)
after=fluree.query(q)['results']['bindings']
assert before==after, 'a re-run changed the shares'
print(f'OK — {len(after)} commitment edges identical across a re-run')"
```

- [ ] **Step 6: Commit**

```bash
git add loaders/load_fluree_wave18.py validators/test_syndicate.py
git commit -m "Wave 18 Task 8: syndicate structure and commitment shares in Fluree

Shares live on reified participation nodes carrying the filing offset —
§C assigns commitments to Fluree, so they exist nowhere else. Member
nodes carry lei + label only; a test asserts no Postgres-owned attribute
leaked in."
```

---

## Task 9: Fluree — the live amendment vote

**Files:**
- Modify: `loaders/load_fluree_wave18.py`, `generators/generate_syndicate_internal.py`
- Test: `validators/test_syndicate.py` (append)

**Interfaces:**
- Produces: `ex:AmendmentVote` nodes and `ex:votesOn` edges with `ex:posture`; amendment events as temporal assertions.

- [ ] **Step 1: Write the failing test**

```python
# append to validators/test_syndicate.py
def test_one_open_amendment_vote_exists():
    assert _n(f"SELECT (COUNT(DISTINCT ?v) AS ?n) FROM <{L}> WHERE {{ "
              f"?v a <{EX}AmendmentVote> ; <{EX}voteState> 'open' }}") >= 1

def test_postures_on_the_open_vote_genuinely_diverge():
    """§F: >= 1 live amendment vote WITH DIVERGENT POSTURES. A vote where
    everyone agrees satisfies the count and not the condition."""
    rows = fluree.query(
        f"SELECT DISTINCT ?posture FROM <{L}> WHERE {{ "
        f"?v a <{EX}AmendmentVote> ; <{EX}voteState> 'open' . "
        f"?e <{EX}votesOn> ?v ; <{EX}posture> ?posture }}"
    )["results"]["bindings"]
    postures = {r["posture"]["value"] for r in rows}
    assert len(postures) >= 2, f"all members hold the same posture: {postures}"

def test_amendment_events_carry_effective_dates():
    n_ev = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
              f"?a a <{EX}AmendmentEvent> }}")
    n_dated = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                 f"?a a <{EX}AmendmentEvent> ; <{EX}effectiveDate> ?d }}")
    assert n_ev >= 1 and n_ev == n_dated
```

- [ ] **Step 2: Run and confirm it fails**

Run: `uv run --with pytest pytest validators/test_syndicate.py -k "vote or amendment" -v`
Expected: FAIL — counts are 0.

- [ ] **Step 3: Generate the vote and load it**

One facility carries an open `AmendmentVote`. Every syndicate member on that facility gets a `votesOn` edge with a `posture` from `{"consent", "decline", "abstain", "undecided"}`. **At least two distinct postures**, and the divergence must be real, not a label — the test above reads the postures, not a `divergent` flag.

Amendment events come from the filings' own amendment articles where dated, and are labelled `public`; postures are `synthetic — internal`.

- [ ] **Step 4: Run tests and commit**

```bash
uv run loaders/load_fluree_wave18.py
uv run --with pytest pytest validators/test_syndicate.py -v
git add loaders/load_fluree_wave18.py generators/generate_syndicate_internal.py \
        sources/screening/wave18_internal.json validators/test_syndicate.py
git commit -m "Wave 18 Task 9: live amendment vote with divergent postures

The divergence is read from the postures themselves, never from a flag."
```

---

## Task 10: Fluree — the two asymmetric disclosure envelopes

**Files:**
- Create: `generators/generate_disclosure_envelopes.py`
- Create: `sources/screening/wave18_envelopes.json`
- Modify: `loaders/load_fluree_wave18.py`
- Test: `validators/test_syndicate.py` (append)

**Interfaces:**
- Produces: `ex:DisclosureEnvelope` nodes carrying `ex:counterparty`, `ex:requestScope` (repeated), `ex:discloseScope` (repeated), `ex:envelopeVersion`, `ex:effectiveFrom`.

**Asymmetric means the two scope sets differ as sets** — what we may request from a counterparty and what we may disclose to it are different. Frequently asymmetric in both directions across the two envelopes.

- [ ] **Step 1: Write the failing test**

```python
# append to validators/test_syndicate.py
def _envelope_scopes():
    rows = fluree.query(
        f"SELECT ?env ?cp ?kind ?elem FROM <{L}> WHERE {{ "
        f"?env a <{EX}DisclosureEnvelope> ; <{EX}counterparty> ?cp . "
        f"{{ ?env <{EX}requestScope> ?elem . BIND('request' AS ?kind) }} "
        f"UNION "
        f"{{ ?env <{EX}discloseScope> ?elem . BIND('disclose' AS ?kind) }} }}"
    )["results"]["bindings"]
    out = {}
    for r in rows:
        env = r["env"]["value"]
        out.setdefault(env, {"request": set(), "disclose": set()})
        out[env][r["kind"]["value"]].add(r["elem"]["value"])
    return out

def test_two_envelopes_exist():
    assert len(_envelope_scopes()) >= 2

def test_at_least_two_envelopes_are_genuinely_asymmetric():
    """§F: >= 2 bilateral envelopes with asymmetric terms.

    Counts ENVELOPES WHOSE TWO SCOPES DIFFER — not envelopes, and not
    scope rows. Compares the sets; reads no `asymmetric` flag."""
    asymmetric = [env for env, s in _envelope_scopes().items()
                  if s["request"] != s["disclose"]]
    assert len(asymmetric) >= 2, (
        f"{len(asymmetric)} of {len(_envelope_scopes())} envelopes differ")

def test_both_scopes_are_non_empty():
    """An envelope with an empty disclose set is trivially 'asymmetric'
    and proves nothing."""
    for env, s in _envelope_scopes().items():
        assert s["request"], f"{env} requests nothing"
        assert s["disclose"], f"{env} discloses nothing"
```

- [ ] **Step 2: Run and confirm it fails**

Run: `uv run --with pytest pytest validators/test_syndicate.py -k envelope -v`
Expected: FAIL — no envelopes.

- [ ] **Step 3: Generate two envelopes and load them**

One per counterparty (Bank of America, Citibank). Scope elements name things that exist — reuse the projection-plan element vocabulary from Task 7. Make the asymmetry meaningful: e.g. we may **request** `own_position` from BofA but may only **disclose** `syndicate_composition` and `amendment_vote_posture` to it.

Versioned (`ex:envelopeVersion`, `ex:effectiveFrom`) because §E gives envelopes a ~365-day `λ_c` and lists renegotiation as a supersession trigger.

- [ ] **Step 4: Run tests and commit**

```bash
uv run generators/generate_disclosure_envelopes.py
uv run loaders/load_fluree_wave18.py
uv run --with pytest pytest validators/test_syndicate.py -v
git add generators/generate_disclosure_envelopes.py \
        sources/screening/wave18_envelopes.json \
        loaders/load_fluree_wave18.py validators/test_syndicate.py
git commit -m "Wave 18 Task 10: two asymmetric bilateral disclosure envelopes

The asymmetry test compares the request and disclose SETS and counts
envelopes whose two scopes differ — not envelopes, not scope rows."
```

---

## Task 11: MongoDB — voting thresholds and assignment provisions

**Files:**
- Create: `loaders/load_mongo_wave18.py`
- Test: `validators/test_syndicate.py` (append)

**Interfaces:**
- Consumes: the six agreements; Wave 15's passage machinery (read `loaders/` for the existing passage-extraction helper before writing a new one — **do not** re-implement it).
- Produces: `document` rows with `doc_type="credit_agreement_wave18"`; `passage` rows with `passage_kind in {"voting_threshold", "assignment_provision"}`, each with `start`/`end` offsets against the stored document text.

- [ ] **Step 1: Write the failing test**

```python
# append to validators/test_syndicate.py
from ccf.config import mongo_db

def test_voting_threshold_passages_exist():
    db = mongo_db(write=False)
    assert db["passage"].count_documents(
        {"passage_kind": "voting_threshold"}) >= 6

def test_assignment_passages_exist():
    db = mongo_db(write=False)
    assert db["passage"].count_documents(
        {"passage_kind": "assignment_provision"}) >= 6

def test_every_wave18_passage_resolves_inside_its_document():
    """A span that does not resolve is a lineage claim nothing supports."""
    db = mongo_db(write=False)
    docs = {d["_id"]: d for d in db["document"].find(
        {"doc_type": "credit_agreement_wave18"})}
    assert docs, "no Wave 18 credit-agreement documents loaded"
    for p in db["passage"].find(
            {"passage_kind": {"$in": ["voting_threshold",
                                      "assignment_provision"]}}):
        doc = docs.get(p["document_id"])
        assert doc, f"passage {p['_id']} points at no loaded document"
        text = doc["text"]
        assert 0 <= p["start"] < p["end"] <= len(text)
        assert text[p["start"]:p["end"]] == p["text"], (
            f"passage {p['_id']} span does not match its own text")

def test_mongo_holds_no_typed_edge():
    """P3: MongoDB holds document text and spans, no typed edges."""
    db = mongo_db(write=False)
    assert db["passage"].count_documents(
        {"passage_kind": {"$in": ["voting_threshold", "assignment_provision"]},
         "participatesIn": {"$exists": True}}) == 0
```

- [ ] **Step 2: Run and confirm it fails**

Run: `uv run --with pytest pytest validators/test_syndicate.py -k "passage or mongo" -v`
Expected: FAIL — counts are 0.

- [ ] **Step 3: Write the loader**

Locate the voting-threshold article by its own language (`"Required Lenders"`, `"each affected Lender"`, `"all Lenders"`, percentage thresholds) and the assignment article by `"Assignment and Assumption"` / `"Successors and Assigns"`. Store the span **and** the exact substring, so the test above can compare them.

Idempotency: upsert on a content-derived `_id`, e.g. `sha256(f"{document}:{start}:{end}").hexdigest()[:16]`.

- [ ] **Step 4: Load, test, commit**

```bash
uv run loaders/load_mongo_wave18.py
uv run --with pytest pytest validators/test_syndicate.py -v
git add loaders/load_mongo_wave18.py validators/test_syndicate.py
git commit -m "Wave 18 Task 11: voting-threshold and assignment passages

Spans store both offsets and the exact substring, so a drifted offset
fails loudly rather than pointing at plausible neighbouring text."
```

---

## Task 12: MongoDB — the Shared National Credit report

**Files:**
- Create: `generators/fetch_snc_report.py`
- Create: `sources/snc/` (fetched PDF + a retrieval record)
- Modify: `loaders/load_mongo_wave18.py`
- Test: `validators/test_syndicate.py` (append)

**Interfaces:**
- Produces: one `document` row `doc_type="snc_annual_report"` with `provenance="public"`, `source`, `retrieved_at`.

- [ ] **Step 1: Locate the report**

It is published jointly by the Federal Reserve, OCC and FDIC. Search `federalreserve.gov` and `occ.gov` for "Shared National Credit Program" annual review. **Record the exact URL and retrieval date** in the artifact and in `docs/ccf_dataprep_v2.md`.

If it cannot be located, **stop and say so** rather than substituting a different publication — §C names this source specifically. Record the gap in `docs/known-issues.md` and mark the §C row `DEFERRED` in Task 17's `spec_coverage.py` entry.

- [ ] **Step 2: Write the failing test**

**PREFLIGHT RULING P4.** If the report cannot be located, the test **skips** on its absence — it is never left failing. A red test masks real failures for the remaining five tasks; the `DEFERRED` row in `spec_coverage.py` is the register that exists to catch a genuinely missing element, and Task 17 Step 3 adds it.

```python
# append to validators/test_syndicate.py
def test_snc_report_is_loaded_with_its_provenance():
    db = mongo_db(write=False)
    doc = db["document"].find_one({"doc_type": "snc_annual_report"})
    if doc is None:
        pytest.skip("SNC report not located — see docs/known-issues.md; "
                    "Task 17 records the §C row as DEFERRED")
    assert doc["provenance"] == "public"
    assert doc["source"].startswith("http"), "no retrievable source URL"
    assert doc["retrieved_at"], "no retrieval date recorded"
    assert len(doc["text"]) > 5000, "the report body did not extract"
```

- [ ] **Step 3: Fetch, extract, load, test**

```bash
uv run generators/fetch_snc_report.py
uv run loaders/load_mongo_wave18.py
uv run --with pytest pytest validators/test_syndicate.py -k snc -v
```

- [ ] **Step 4: Commit**

```bash
git add generators/fetch_snc_report.py loaders/load_mongo_wave18.py \
        sources/snc validators/test_syndicate.py
git commit -m "Wave 18 Task 12: Shared National Credit annual report"
```

---

## Task 13: SQLite — the syndicate desk tracker

**Files:**
- Create: `loaders/load_sqlite_wave18.py`
- Test: `validators/test_syndicate.py` (append)

**Interfaces:**
- Produces: `syndicate_desk_tracker` in `data/departmental.sqlite`, alongside the existing five tables.

- [ ] **Step 1: Write the failing test**

```python
# append to validators/test_syndicate.py
import sqlite3
from ccf.config import SQLITE_PATH

def _sqlite(sql):
    with sqlite3.connect(SQLITE_PATH) as con:
        return con.execute(sql).fetchall()

def test_desk_tracker_exists_and_is_populated():
    assert _sqlite("SELECT count(*) FROM syndicate_desk_tracker")[0][0] >= 6

def test_tracker_rows_reference_real_facilities():
    from ccf.config import pg_connect, PG_SCHEMA_V2 as S
    tracked = {r[0] for r in _sqlite(
        "SELECT DISTINCT facility_id FROM syndicate_desk_tracker")}
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT facility_id FROM "{S}".facility')
        known = {r[0] for r in cur.fetchall()}
    assert tracked <= known, f"tracker names unknown facilities: {tracked - known}"

def test_tracker_is_departmental_only():
    """P4: SQLite holds departmental material. If the desk's note were
    also in Postgres, the departmental-store narrative would be a fiction."""
    from ccf.config import pg_connect, PG_SCHEMA_V2 as S
    with pg_connect() as c, c.cursor() as cur:
        cur.execute("SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema=%s AND table_name LIKE %s",
                    (S, "%desk_tracker%"))
        assert cur.fetchone()[0] == 0
```

- [ ] **Step 2: Run and confirm it fails**

Run: `uv run --with pytest pytest validators/test_syndicate.py -k tracker -v`
Expected: FAIL — `sqlite3.OperationalError: no such table: syndicate_desk_tracker`

- [ ] **Step 3: Write the loader**

Follow `loaders/load_sqlite_wave17.py`. Columns: `tracker_id TEXT PRIMARY KEY`, `facility_id TEXT NOT NULL`, `desk_note TEXT NOT NULL`, `internal_flag TEXT NOT NULL`, `updated_at TEXT NOT NULL`, `provenance TEXT NOT NULL`. `tracker_id` is content-keyed. Upsert with `ON CONFLICT(tracker_id) DO UPDATE`.

At least one note per selected facility, and at least one note that records a **posture the desk holds and the credit file does not** — the departmental store exists to be reached for something no other store has.

- [ ] **Step 4: Load, test, commit**

```bash
uv run loaders/load_sqlite_wave18.py
uv run --with pytest pytest validators/test_syndicate.py -v
git add loaders/load_sqlite_wave18.py validators/test_syndicate.py
git commit -m "Wave 18 Task 13: syndicate desk tracker in the departmental store"
```

---

## Task 14: The peer estate — positions at two precisions

**Files:**
- Create: `generators/generate_peer_positions.py`
- Create: `sources/screening/wave18_peer.json`
- Create: `loaders/load_peer_wave18.py`
- Test: `validators/test_syndicate.py` (append)

**Interfaces:**
- Produces: on the PEER fabric — `colender.peer_position`, `colender.peer_product_declaration`; peer Fluree nodes for the two counterparty identities.
- `load_peer(dry_run: bool = False) -> dict` returning counts.

**Every peer write gates on `assert_distinct_fabrics()`, `assert_co_lender_schema()`, and an explicit `current_database()` assertion, in that order, before any DDL.**

- [ ] **Step 1: Write the failing test**

```python
# append to validators/test_syndicate.py
from ccf.config import (co_lender_configured, co_lender_pg_connect,
                        CO_LENDER_PG_SCHEMA as PS, assert_distinct_fabrics)

def _peer(sql, params=None):
    if not co_lender_configured():
        pytest.skip("peer fabric not configured in this shell")
    with co_lender_pg_connect() as c, c.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()

def test_the_two_fabrics_are_still_distinct():
    assert_distinct_fabrics()

def test_peer_writes_landed_in_the_peer_database():
    db = _peer("SELECT current_database()")[0][0]
    assert db == "bofa_syndicated", f"peer rows went to {db!r}"

def test_two_counterparty_identities_exist():
    got = {r[0] for r in _peer(
        f'SELECT DISTINCT counterparty FROM "{PS}".peer_position')}
    assert len(got) >= 2, f"only {got} on the peer fabric"

def test_one_counterparty_discloses_exactly_and_one_only_a_band():
    rows = _peer(f'SELECT counterparty, share_usd, band_low, band_high '
                 f'FROM "{PS}".peer_position')
    exact = {r[0] for r in rows if r[1] is not None}
    banded = {r[0] for r in rows if r[1] is None
              and r[2] is not None and r[3] is not None}
    assert exact and banded, f"exact={exact} banded={banded}"
    assert not (exact & banded), (
        "a counterparty discloses both ways; the precision is then not a "
        "property of the counterparty and the floor proves nothing")

def test_the_band_peer_has_no_exact_figure_anywhere_on_the_peer_fabric():
    """§F's mixed-precision floor is only real if the band cannot be
    resolved to a number. Checks the DENOMINATOR independently — every
    row for that counterparty, not just the rows flagged as banded."""
    banded = {r[0] for r in _peer(
        f'SELECT DISTINCT counterparty FROM "{PS}".peer_position '
        f'WHERE share_usd IS NULL')}
    for cp in banded:
        leaks = _peer(f'SELECT count(*) FROM "{PS}".peer_position '
                      f'WHERE counterparty = %s AND share_usd IS NOT NULL',
                      (cp,))[0][0]
        assert leaks == 0, f"{cp} has {leaks} exact figures despite banding"

def test_the_band_is_not_a_point():
    """A band whose bounds are equal is an exact figure wearing a costume."""
    degenerate = _peer(f'SELECT counterparty, band_low, band_high '
                       f'FROM "{PS}".peer_position '
                       f'WHERE band_low IS NOT NULL AND band_low >= band_high')
    assert not degenerate, f"degenerate bands: {degenerate}"
```

- [ ] **Step 2: Run and confirm it fails**

Run: `bash -ic 'uv run --with pytest pytest validators/test_syndicate.py -k peer -v'`
Expected: FAIL — `relation "colender.peer_position" does not exist`

- [ ] **Step 3: Write the peer loader**

```python
def _assert_peer_target(cur) -> None:
    """Three gates, in order, before any DDL touches the peer.

    Both databases sit on 192.168.4.76:5432 and differ by nothing but a
    name. A one-character difference is not something to trust an eye with.
    """
    assert_distinct_fabrics()
    assert_co_lender_schema(CO_LENDER_PG_SCHEMA)
    cur.execute("SELECT current_database(), current_user")
    db, user = cur.fetchone()
    if db != "bofa_syndicated" or user != "colender":
        raise FabricBoundaryError(
            f"refusing to write: connected to {db!r} as {user!r}, "
            f"expected 'bofa_syndicated' as 'colender'")
```

```sql
CREATE TABLE IF NOT EXISTS "colender".peer_position (
    position_id     TEXT PRIMARY KEY,
    counterparty    TEXT NOT NULL,
    facility_id     TEXT NOT NULL,
    -- Exactly one of (share_usd) or (band_low, band_high) is populated.
    -- A counterparty that discloses at band granularity must have NO
    -- exact figure anywhere on this fabric, or the mixed-precision floor
    -- is theatre. Enforced by CHECK and re-proved live in Task 16.
    share_usd       NUMERIC NULL,
    band_low        NUMERIC NULL,
    band_high       NUMERIC NULL,
    internal_rating TEXT NOT NULL,
    workout_posture TEXT NOT NULL,
    as_of           DATE NOT NULL,
    provenance      TEXT NOT NULL,
    CHECK ((share_usd IS NOT NULL AND band_low IS NULL AND band_high IS NULL)
        OR (share_usd IS NULL AND band_low IS NOT NULL AND band_high IS NOT NULL
            AND band_low < band_high))
);
```

Bank of America gets `share_usd`; Citibank gets `band_low`/`band_high` only. Bands must be wide enough that the midpoint is not the true figure — a band centred on the answer leaks it.

- [ ] **Step 4: Load, test, and re-run the isolation validator**

```bash
bash -ic 'uv run loaders/load_peer_wave18.py'
bash -ic 'uv run validators/test_fabric_isolation.py'   # must still be 7/7
bash -ic 'uv run --with pytest pytest validators/test_syndicate.py -v'
```

- [ ] **Step 5: Commit**

```bash
git add generators/generate_peer_positions.py loaders/load_peer_wave18.py \
        sources/screening/wave18_peer.json validators/test_syndicate.py
git commit -m "Wave 18 Task 14: peer positions at two disclosure precisions

BofA exact, Citibank band-only, enforced by CHECK and re-proved live.
Three gates before any peer DDL — distinct fabrics, schema, and an
explicit current_database() assertion."
```

---

## Task 15: Peer product declarations — timeout, attestation, TTL

**Files:**
- Modify: `generators/generate_peer_positions.py`, `loaders/load_peer_wave18.py`
- Modify: `loaders/load_postgres_wave18.py` (the `context_debt` row on our side)
- Test: `validators/test_syndicate.py` (append)

**Interfaces:**
- Produces: `colender.peer_product_declaration (declaration_id, counterparty, product_id, declared_ttl_seconds, declared_latency_ms, attestation JSONB NULL, provenance)`; one `ccf_v2.context_debt` row recording the unattested claim.

These three are the §F conditions that sound like behaviour. **They are declarations.** The SDK reads them and acts; we do not act.

- [ ] **Step 1: Write the failing test**

```python
# append to validators/test_syndicate.py
DEFAULT_MAX_FEDERATION_LATENCY_MS = 5000  # §B: max_federation_latency, 5s

def test_one_declaration_exceeds_the_default_latency_bound():
    """§F: >= 1 federated request that times out, so fail-closed is
    observed. Recomputed: declared latency vs. the declared bound."""
    slow = _peer(f'SELECT counterparty, declared_latency_ms '
                 f'FROM "{PS}".peer_product_declaration '
                 f'WHERE declared_latency_ms > %s',
                 (DEFAULT_MAX_FEDERATION_LATENCY_MS,))
    assert slow, "no declaration would breach the 5s default bound"

def test_not_every_declaration_is_slow():
    """A fabric where every peer times out demonstrates nothing about
    fail-closed — it just looks broken."""
    fast = _peer(f'SELECT count(*) FROM "{PS}".peer_product_declaration '
                 f'WHERE declared_latency_ms <= %s',
                 (DEFAULT_MAX_FEDERATION_LATENCY_MS,))[0][0]
    assert fast >= 1

def test_exactly_one_claim_is_unattested():
    """§F: >= 1 unattested remote claim, so Context Debt is exercised.
    Asserts the absence is genuine AND that it is the intended one."""
    rows = _peer(f'SELECT declaration_id, attestation '
                 f'FROM "{PS}".peer_product_declaration')
    unattested = [r[0] for r in rows if r[1] is None]
    assert len(unattested) == 1, (
        f"{len(unattested)} unattested declarations; the floor needs "
        f"exactly one so the case is identifiable")
    assert len(rows) > 1, "everything is unattested; nothing is contrasted"

def test_the_unattested_claim_is_recorded_as_context_debt_on_our_side():
    n = _pg(f'SELECT count(*) FROM "{S}".context_debt '
            f"WHERE reason LIKE '%unattested%'")[0][0]
    assert n >= 1

def test_a_remote_ttl_binds_below_the_local_composite():
    """§F: >= 1 remote product with a shorter TTL than the local composite
    would otherwise carry. §B puts the local TTL at 4 hours."""
    LOCAL_TTL_SECONDS = 4 * 60 * 60
    ttls = [r[0] for r in _peer(
        f'SELECT declared_ttl_seconds FROM "{PS}".peer_product_declaration')]
    assert ttls, "no declarations"
    assert min(ttls) < LOCAL_TTL_SECONDS, (
        f"shortest remote TTL is {min(ttls)}s; the local composite is "
        f"{LOCAL_TTL_SECONDS}s, so the TTL floor never binds")
    assert max(ttls) >= LOCAL_TTL_SECONDS, (
        "every remote TTL is short, so the floor binds trivially and the "
        "'shortest of them' rule is untested")
```

- [ ] **Step 2: Run and confirm it fails**

Run: `bash -ic 'uv run --with pytest pytest validators/test_syndicate.py -k "latency or attest or ttl or debt" -v'`
Expected: FAIL — `relation "colender.peer_product_declaration" does not exist`

- [ ] **Step 3: Generate and load the declarations**

At least three declarations so each condition has a contrast case:
- one normal (fast, attested, TTL ≥ 4h);
- one slow (`declared_latency_ms > 5000`), attested;
- one unattested (`attestation IS NULL`) with a short TTL (`declared_ttl_seconds < 14400`).

Write the matching `context_debt` row on **our** side, since the debt is ours to carry, not the peer's.

**PREFLIGHT RULING P2 — the exact shape of that write.** `ccf_v2.context_debt` has 303 rows, columns `(debt_id, accession, covenant_type, reason, recorded_at, subject_kind, subject_key)`, a serial PK (`nextval('context_debt_debt_id_seq')`) and **no unique constraint** on `(subject_kind, subject_key)`. So:

- **Never supply `debt_id`** — the sequence assigns it.
- **Guard the insert**, or a re-run adds a second row and the loader is not idempotent:

```python
cur.execute(
    f'INSERT INTO "{S}".context_debt '
    "(reason, recorded_at, subject_kind, subject_key) "
    "SELECT %s, %s, 'federation_attestation', %s "
    "WHERE NOT EXISTS (SELECT 1 FROM \"" + S + "\".context_debt "
    "  WHERE subject_kind = 'federation_attestation' AND subject_key = %s)",
    (reason, recorded_at, declaration_id, declaration_id))
```

- **Do not add a constraint** to `context_debt` — another wave owns it.

- [ ] **Step 4: Test and commit**

```bash
bash -ic 'uv run loaders/load_peer_wave18.py'
uv run loaders/load_postgres_wave18.py
bash -ic 'uv run --with pytest pytest validators/test_syndicate.py -v'
git add generators/generate_peer_positions.py loaders/load_peer_wave18.py \
        loaders/load_postgres_wave18.py sources/screening/wave18_peer.json \
        validators/test_syndicate.py
git commit -m "Wave 18 Task 15: timeout, attestation and TTL declarations

Three declarations so each condition has a contrast case — a fabric where
every peer is slow, or everything unattested, demonstrates nothing."
```

---

## Task 16: `validators/syndicate.py` — the six floors

**Files:**
- Create: `validators/syndicate.py`
- Test: `validators/test_syndicate.py` (append — tests of the VALIDATOR itself)

**Interfaces:**
- Produces: six functions each `(ctx: Context | None = None) -> tuple[bool, str]`, a `FLOORS` list of `(label, fn)`, and `main() -> int`. Task 17 imports these by name.

Model the file on `validators/aml_typology.py` exactly — same docstring stance ("this is a build-time validator, not an operator"), a `load_context()` taking one snapshot, `FLOORS`, `render()`, `main()` printing `N passed · M failed`.

The six floors:

| Function | Proves |
|---|---|
| `shares_are_sourced` | Every share's cited offset resolves, in the source filing, to the lender name it claims, with its amount present at that row — **no share was invented** |
| `envelopes_are_asymmetric` | ≥ 2 envelopes whose request-set ≠ disclose-set, compared as sets |
| `precision_is_mixed` | One counterparty exact, one band-only, and the band peer has no exact figure derivable anywhere |
| `vote_postures_diverge` | The open vote carries ≥ 2 distinct postures, read from the postures |
| `federation_bounds_bind` | ≥ 1 declared latency > the declared bound; ≥ 1 unattested with a contrast; min remote TTL < local composite < max remote TTL |
| `lineage_is_separable` | Every peer-sourced element is distinguishable from a local one — no peer claim is reachable through a path that marks it local |

- [ ] **Step 1: Read why `shares_reconcile` was deleted — do not reinstate it**

**PREFLIGHT RULING T16-PRE, measured 2026-08-25.** An earlier version of this plan required every facility's parsed shares to sum to its recorded `commitment_amount`. **That floor rests on a false premise and has been deleted.** Measured across all twelve Wave 18 facilities: *not one reconciles*. Best case 4.0% off (Paychex); worst 3391%.

Four causes, all legitimate, none a Wave 18 defect:

1. **Placeholder rows.** Bausch's term-loan schedule is JPMorgan $1,285,342,270.46 plus *"Cashless Option Initial Lenders [on file with the Administrative Agent]"* $1,039,657,729.54. Task 2 correctly excludes the placeholder — it names no institution — so the parsed sum is short by $1.04bn **the filing itself declines to attribute to anyone**.
2. **Amendment exhibits.** Regis's exhibit lists only *incremental* commitments ($5M Term A + $10M Term B), not the standing syndicate.
3. **Unreliable tranche captions.** All 17 AHR rows sit under one caption though they span a revolver and a term loan.
4. **Wave 4 totals that are themselves wrong.** AHR's `FAC-2A2C38` carries $35,000,000 against $1.222bn of filed rows — the class already recorded as known-issues #32.

Reconciling against the *filing's own* TOTAL line instead of Wave 4's derived column was also checked and closed: the six filings do not reliably state one.

**So the floor must not depend on `ccf_v2.facility.commitment_amount` at all.** The weaker variant "no single share exceeds its facility" also fails, on AHR, because that total is itself a mis-extraction.

`shares_are_sourced` replaces it: for every `SyndicateParticipation` node, re-extract the source document, take the node's `ex:sourcePassage` offset, and require that the text there resolves to the lender name the node claims, with its amount present at that row. That proves **no share was invented**, which is the property that actually matters, and unlike summation it is both true and checkable.

Record the four causes in `docs/ccf_dataprep_v2.md` and `docs/known-issues.md` so nobody re-derives the deleted floor.

- [ ] **Step 2: Write the failing test for the validator itself**

Every arm must be tested against a known-present **and** a known-absent input and required to give **different answers**. A checker that returns the same answer either way has hidden defects for seven waves in this repo before.

```python
# append to validators/test_syndicate.py
from validators import syndicate

def test_every_floor_returns_a_two_tuple():
    ctx = syndicate.load_context()
    for label, fn in syndicate.FLOORS:
        ok, detail = fn(ctx)
        assert isinstance(ok, bool), f"{label} returned {ok!r}"
        assert isinstance(detail, str) and detail, f"{label} gave no detail"

def test_asymmetry_checker_says_no_when_scopes_match():
    """Feed it a context where every envelope's two scopes are identical.
    If it still passes, it is not reading the scopes."""
    ctx = syndicate.load_context()
    for env in ctx.envelopes.values():
        env["disclose"] = set(env["request"])
    ok, detail = syndicate.envelopes_are_asymmetric(ctx)
    assert not ok, f"passed on symmetric envelopes: {detail}"

def test_asymmetry_checker_says_yes_on_the_real_estate():
    ok, detail = syndicate.envelopes_are_asymmetric(syndicate.load_context())
    assert ok, detail

def test_posture_checker_says_no_when_all_postures_agree():
    ctx = syndicate.load_context()
    ctx.vote_postures = {k: "consent" for k in ctx.vote_postures}
    ok, detail = syndicate.vote_postures_diverge(ctx)
    assert not ok, f"passed on unanimous postures: {detail}"

def test_precision_checker_says_no_when_the_band_peer_gains_a_figure():
    ctx = syndicate.load_context()
    for row in ctx.peer_positions:
        if row["share_usd"] is None:
            row["share_usd"] = 75_000_000
            break
    ok, detail = syndicate.precision_is_mixed(ctx)
    assert not ok, f"passed after the band peer disclosed exactly: {detail}"

def test_ttl_checker_says_no_when_every_remote_ttl_is_long():
    ctx = syndicate.load_context()
    for d in ctx.declarations:
        d["declared_ttl_seconds"] = 86_400
    ok, detail = syndicate.federation_bounds_bind(ctx)
    assert not ok, f"passed when no remote TTL binds: {detail}"
```

**PREFLIGHT RULING P3 — `Context` is a mutable dataclass holding snapshots**, never live cursors, same stance as `aml_typology.Context`. The tests above mutate it, so these field shapes are binding:

```python
@dataclass
class Context:
    as_of: str
    #: envelope IRI -> {"request": set[str], "disclose": set[str]}
    envelopes: dict[str, dict[str, set[str]]]
    #: voter IRI -> posture string, for the ONE open vote
    vote_postures: dict[str, str]
    #: rows of colender.peer_position, column names as keys
    peer_positions: list[dict]
    #: rows of colender.peer_product_declaration, column names as keys
    declarations: list[dict]
    #: facility_id -> {"parsed_sum": int, "recorded_total": int}
    share_totals: dict[str, dict[str, int]]
    #: element name -> "local" | "remote", for lineage_is_separable
    element_origin: dict[str, str]
```

> **CORRECTION, controller Ruling T16-R1 (2026-08-26) — `share_totals` was
> REMOVED and is not in the shipped `Context`.** Its two members are the
> inputs of `shares_reconcile`, the floor Ruling T16-PRE deleted after
> measuring that not one of the twelve Wave 18 facilities reconciles. A
> populated-but-unread field holding `recorded_total` is how a deleted
> condition survives its deletion. `shares_are_sourced` does not need it:
> it re-extracts the source document, takes the node's `ex:sourcePassage`
> offset, and checks the text there resolves to the lender the node claims
> with its amount at that row. The other five field shapes above are
> binding as written. `element_origin` shipped as a read-only **property**
> derived from `element_probes` -- which fabric actually answered -- rather
> than a stored field, per the same ruling. See `docs/known-issues.md` §34.

- [ ] **Step 3: Run and confirm it fails**

Run: `bash -ic 'uv run --with pytest pytest validators/test_syndicate.py -k "floor or checker" -v'`
Expected: FAIL — `ModuleNotFoundError: No module named 'validators.syndicate'`

- [ ] **Step 4: Write `validators/syndicate.py`**

Reminders that have cost this repo waves before:
- **Recompute; never read a flag.** No `is_asymmetric`, no `granularity`, no `divergent` column may be consulted.
- **Count the unit the condition names.** "≥ 2 asymmetric envelopes" counts envelopes whose two scopes differ.
- **Count the denominator independently.** `precision_is_mixed` must enumerate *every* row for the band counterparty, not only rows already flagged as banded — a check that selects by the property it polices cannot see it missing.
- Each floor's returned `detail` states the numbers it measured, so a future reader can see what it actually computed.

- [ ] **Step 5: Run the validator and the tests**

```bash
bash -ic 'uv run validators/syndicate.py'
bash -ic 'uv run --with pytest pytest validators/test_syndicate.py -v'
```
Expected: `6 passed · 0 failed`, and the full test file green.

- [ ] **Step 6: Commit**

```bash
git add validators/syndicate.py validators/test_syndicate.py
git commit -m "Wave 18 Task 16: the six §F floors, recomputed live

Every arm is tested against a known-present AND a known-absent input and
required to give different answers. The share tolerance is measured from
the filings' own rounding rather than chosen."
```

---

## Task 17: Registration and close-out

**Files:**
- Modify: `validators/conditions.py`, `validators/partition.py`, `validators/spec_coverage.py`
- Modify: `docs/ccf_dataprep_v2.md`, `docs/HANDOFF.md`, `docs/known-issues.md`

**Interfaces:**
- Consumes: `validators.syndicate.FLOORS` and the six floor functions by name.

- [ ] **Step 1: Register the conditions**

Add a `--- #20 syndicated-lending-co-lender (Wave 18) ---` block to `collect()` in `validators/conditions.py`, following the Wave 17 block at `:2007` exactly. Direct counts go against the stores; the six ordering/absence conditions delegate to `validators/syndicate.py` through a `_run_syndicate_floor` helper modelled on `_run_aml_floor`.

Direct counts to register: syndicate members ≥ 25; syndicated facilities with parsed schedules ≥ 6; disclosure envelopes ≥ 2; peer counterparty identities ≥ 2; peer product declarations ≥ 3.

- [ ] **Step 2: Extend the partition validator in BOTH directions**

`partition.py` cannot see a *missing* element — that is `spec_coverage.py`'s half. What it must gain here:

- `syndicate_member` carries no commitment/share/envelope column (Postgres does not hold Fluree's slice).
- Fluree `FinanceSyndicateMember` nodes carry no Postgres-owned attribute.
- `syndicate_desk_tracker` appears in SQLite and in no other store.
- **New direction, specific to this wave:** no peer-owned element appears in our stores, and no element of ours appears in the peer's. Add both arms — a one-directional check would pass while the boundary leaked.
- Add the new `ex:` types to `PERMITTED_EX_TYPES` and the new columns to `POSTGRES_OWNED_ATTRS`.

- [ ] **Step 3: Map every §C row in `spec_coverage.py`**

Add a `SYNDICATED_CO_LENDER` list and register it in `MANIFEST`. All sixteen §C rows get a `Mapping` — `PROBE` with a live count where the element exists, `DEFERRED` where it genuinely does not (the SNC report if Task 12 could not locate it), each with a `divergence` string where the estate delivered something narrower than §C asked.

Match `§C` by **name, case-insensitively** — section letters are not stable across standard versions.

- [ ] **Step 4: Run everything and read the PASS counts**

```bash
bash -ic 'uv run validators/conditions.py'
bash -ic 'uv run validators/partition.py'
bash -ic 'uv run validators/syndicate.py'
bash -ic 'uv run validators/test_fabric_isolation.py'
bash -ic 'uv run validators/spec_coverage.py --product syndicated-lending-co-lender'
bash -ic 'uv run --with pytest pytest validators/ -q'
```

Read the **PASS count** from each, never the "0 failed" line. Record the actual numbers in the handoff — do not write "all green" without them.

- [ ] **Step 5: Update the documentation**

- `docs/ccf_dataprep_v2.md`: entity tables, row counts, file names, and the binding table additions from Task 4. This is the contract the SDK project reads.
- `docs/HANDOFF.md`: replace the Wave 17 state block. It is currently **stale** — it says Wave 17 is unmerged when `main` is at `2be7abb` with Wave 17 merged. Fix that while you are here.
- `docs/known-issues.md`: anything found and not fixed, including the SNC gap if it stands and the peer Mongo password that wants rotating.

- [ ] **Step 6: Grep the estate for names of anything you deleted or renamed**

Deleted conditions leave their names behind — six instances in this repo's history.

```bash
grep -rn "syndicate" docs/ validators/ loaders/ generators/ --include="*.py" --include="*.md" \
  | grep -iv "wave18\|dbt-dln\|FinanceSyndicate" | head -40
```

- [ ] **Step 7: Commit**

```bash
git add validators/conditions.py validators/partition.py \
        validators/spec_coverage.py docs/ccf_dataprep_v2.md \
        docs/HANDOFF.md docs/known-issues.md
git commit -m "Wave 18 Task 17: register syndicated-lending-co-lender

Conditions, partition (both directions across the fabric boundary), and
§C coverage. Also corrects docs/HANDOFF.md, which still claimed Wave 17
was unmerged."
```

---

## Self-Review

**Spec coverage** — every section of `docs/wave18-design.md` maps to a task:

| Design section | Tasks |
|---|---|
| §1 scope / the line | Global Constraints; no task builds a client or server |
| §2 what exists | Tasks 1, 5 (reuse `facility`, `crosswalk`, `context_debt`) |
| §3 six agreements | Task 2 |
| §4 semantic binding | Task 4 |
| §5 our estate — Fluree | Tasks 8, 9, 10 |
| §5 our estate — Postgres | Tasks 5, 6, 7 |
| §5 our estate — Mongo | Tasks 11, 12 |
| §5 our estate — SQLite | Task 13 |
| §6 peer estate, two identities | Task 14 |
| §7 the nine §F conditions | Tasks 2, 3, 10, 14, 15, 16 |
| §8 validation and registration | Tasks 16, 17 |
| §9 agent repair | Task 1 |
| §10 not built | no task; `sharesCollateralWith` bound in Task 4, edges deliberately unpopulated |
| §11 open items | Task 12 (SNC); the eleven-vs-six question is settled in Task 2's `AGREEMENTS` table |

**Type consistency** — `member_id` is `SYNM-<8 hex>` in Tasks 3, 5, 8. `extract_agent` returns `{"name", "offset"}` in Tasks 1 and 8. `parse_schedule` returns `lender_raw`/`amount_usd`/`offset`/`tranche` in Tasks 2, 3, 8, 16. Floor functions are `(ctx) -> (bool, str)` in Tasks 16 and 17. `Context` is mutable in Task 16 because the tests mutate it.

**Gap found and closed during review:** Task 16's `lineage_is_separable` floor had no §F row behind it — §D's validation gates name "lineage provenance separation" but §F does not list it as a `≥ N`. It is kept as a floor because §B calls federated lineage "the novel contract element", and it is registered in Task 17 as a **safety property**, not a §F condition — the same treatment Wave 17 gave `no_path_to_real_entity`.
