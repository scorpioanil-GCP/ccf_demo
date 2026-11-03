#!/usr/bin/env python3
"""Wave 19 Task 11 — the risk-department limit workbook, into SQLite.

`large-exposure-rwa-concentration` §C assigns SQLite one element: a
"risk-department limit workbook" — the department's own spreadsheet-shaped
tracking sheet, distinct from the FORMAL policy binding Task 9 already wrote
into Fluree (`ex:RegimeVersion`-shaped nodes: CRR, PRA, Reg O, and the
internal appetite, each `citesProvision`). Fluree remains the single writer
for the appetite LEVEL and is what `validators/large_exposure.py` (Task 15)
reads for every recomputation — this table is never consulted as an input to
a floor. What belongs here instead is what a real risk department layers on
top of a formal limit: a sector-level early-warning tier nobody formalized,
a monitoring flag on a specific book, an informal Reg O tracking note — the
kind of thing that lives in a shared spreadsheet, not the policy engine.

## Table name — deliberately NOT `risk_limit_workbook`

That name is already taken. Wave 7's `load_sqlite_wave7.py` created a table
called `risk_limit_workbook` for `mnpi-wall-enforcement` — per-obligor and
per-sector exposure limits with a stored `utilisation` column, keyed
`limit_id` (`LIM-0000` …). `conditions.py`'s Wave 7 registration
(`"departmental tables populated"`) enumerates that literal name and would
break if it were repointed at a different schema, and `utilisation` is
exactly the kind of stored derived figure this wave's own brief forbids
("do not store a computed utilisation or breach flag anywhere"). Task 11's
brief names the same string for a table with a DIFFERENT schema
(`line_id`, `group_label`, `limit_intent`, `limit_pct`, `note`, `owner`,
`reviewed_on`, `provenance`) — an unnoticed collision, not an instruction to
widen or replace Wave 7's table. This project already has a convention for
exactly this situation: `aml_projection_plan`, `ib_projection_plan`, and
`syndicate_projection_plan` all prefix a name Wave 7's `projection_plan`
already held, rather than colliding with it. This table follows the same
convention: `large_exposure_limit_workbook`. See the Wave 19 Task 11 report
for the check performed before writing this file.

## The leak path

Every `note` is free text about the department's OWN internal appetite
envelope — never a claim about the real reporting bank's regulatory
standing. "One group is being tracked against our internal appetite" is
what these notes say; none of them assert that the real institution is over
a REGULATORY limit, because none of them are — the whole point of Task 9's
engineered appetite is a group that breaches HOUSE policy while remaining
compliant under CRR and PRA's 25%. The reporting bank itself is never named
in any note (first person -- "our", "we" -- throughout instead); only a
sector-level, non-identifying label is used for the group under monitoring.
`validators/large_exposure.py` (Task 15) enumerates every workbook line,
including this free text, to confirm none of it reads as an assertion of a
real breach.

## Numbers cited, not invented twice

Row `LEW-001` and `LEW-003` cite the internal appetite's `limit_pct_of_capital`
by reading it live from `sources/screening/wave19_limit_envelope.json` — the
artifact Task 9's generator wrote after re-deriving the figure against the
loaded estate and asserting the bounds check. This loader does not
re-derive or re-check that figure; it only restates a value some other
process already verified, so a change to the appetite level does not
require this loader to be hand-edited to match. What is NOT read from
anywhere and NOT stored anywhere is any group's MEASURED position against
that appetite (e.g. the ~5.41% headline figure) — that is exactly the
derived-and-recomputed-only value the wave's global constraints name.

## Idempotent

`INSERT ... ON CONFLICT(line_id) DO UPDATE`, keyed on `line_id`, a
content-derived string chosen at generation time — never a row's position
in this file or in the table.

    uv run loaders/load_limit_workbook.py --dry-run
    uv run loaders/load_limit_workbook.py
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys

from ccf.config import REPO_ROOT, SQLITE_PATH

SCREEN = REPO_ROOT / "sources" / "screening"
ENVELOPE = SCREEN / "wave19_limit_envelope.json"

TABLE = "large_exposure_limit_workbook"

DDL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    line_id       TEXT PRIMARY KEY,
    group_label   TEXT NOT NULL,
    limit_intent  TEXT NOT NULL,
    limit_pct     REAL,
    note          TEXT NOT NULL,
    owner         TEXT NOT NULL,
    reviewed_on   TEXT NOT NULL,
    provenance    TEXT NOT NULL
);
"""

REVIEWED_ON = "2026-08-27"


def internal_appetite_pct() -> float:
    """Read the internal appetite level Task 9 already derived and verified.

    Raises rather than falling back to a hard-coded 5.0 -- a silent
    fallback here would let this loader drift from Task 9's artifact
    without ever being noticed, exactly the "counted but not created"
    failure CLAUDE.md warns about, just for a number instead of a row.
    """
    if not ENVELOPE.exists():
        raise FileNotFoundError(
            f"{ENVELOPE} is absent -- run generators/generate_limit_envelope.py "
            "(Task 9) before this loader; the internal appetite level is not "
            "re-derived here, only cited.")
    data = json.loads(ENVELOPE.read_text())
    return float(data["internal_appetite"]["limit_pct_of_capital"])


def build_rows(appetite_pct: float) -> list[tuple]:
    """The workbook lines. Five, none of them a per-group utilisation
    figure, none of them naming the reporting bank.

    (line_id, group_label, limit_intent, limit_pct, note, owner,
     reviewed_on, provenance)
    """
    return [
        (
            "LEW-001",
            "firm-wide",
            "single connected-group exposure appetite",
            appetite_pct,
            "House-set ceiling on our aggregate exposure to any single "
            "connected obligor group, expressed as a share of our own "
            "tier 1 capital base. Set intentionally below the CRR/PRA "
            "large-exposure ceiling as a matter of internal risk "
            "appetite, not a regulatory requirement -- a group can sit "
            "inside this line and still be measured separately against "
            "the regulatory limit, and the two are not the same test.",
            "credit-risk",
            REVIEWED_ON,
            "synthetic — internal",
        ),
        (
            "LEW-002",
            "sector — pharmaceuticals & specialty health",
            "sector concentration early-warning threshold",
            round(appetite_pct - 0.5, 4),
            "Department-set early-warning tier for concentration "
            "building within the pharmaceuticals and specialty-health "
            "sector, held tighter than the firm-wide single-group "
            "appetite (line LEW-001) so credit officers get a heads-up "
            "before any one relationship approaches the harder line "
            "above. A purely internal working threshold with no "
            "regulatory counterpart.",
            "credit-risk",
            REVIEWED_ON,
            "synthetic — internal",
        ),
        (
            "LEW-003",
            "connected group under enhanced monitoring — "
            "pharmaceuticals & specialty health sector",
            "enhanced monitoring against the single connected-group "
            "appetite",
            appetite_pct,
            "One connected obligor group in the pharmaceuticals and "
            "specialty-health sector is being tracked here as "
            "approaching our internal single-group exposure appetite "
            "(line LEW-001). This is a house-appetite flag only: the "
            "same group has separately been checked against the CRR "
            "and PRA large-exposure ceiling and sits comfortably inside "
            "it. Nothing here implies that a regulatory limit has been "
            "reached or exceeded, by us or by the group -- this line "
            "exists purely for ongoing credit-committee visibility "
            "against our own internal threshold.",
            "credit-risk",
            REVIEWED_ON,
            "synthetic — engineered",
        ),
        (
            "LEW-004",
            "Regulation O — insider and related-party extensions of "
            "credit",
            "informational tracking ahead of the board pre-approval "
            "threshold",
            None,
            "Routine departmental tracking of insider and "
            "related-party extensions of credit ahead of the board "
            "pre-approval threshold under Regulation O. This book "
            "flags names for committee review before any approval "
            "decision is required; it does not itself record an "
            "approval, a denial, or a breach.",
            "compliance",
            REVIEWED_ON,
            "synthetic — internal",
        ),
        (
            "LEW-005",
            "firm-wide",
            "workbook review cadence",
            None,
            "This workbook is reviewed on a standing cadence by the "
            "credit-risk function. This line records that the review "
            "occurred; it does not itself carry a limit.",
            "credit-risk",
            REVIEWED_ON,
            "synthetic — internal",
        ),
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    appetite_pct = internal_appetite_pct()
    rows = build_rows(appetite_pct)

    print("Wave 19 Task 11 — SQLite load: "
          f"{TABLE}\n")
    print(f"  internal appetite (from Task 9's artifact): {appetite_pct}% "
          "of tier 1")
    print(f"  {len(rows)} workbook lines")
    engineered = [r for r in rows if r[7] == "synthetic — engineered"]
    print(f"  {len(engineered)} engineered row(s): "
          f"{[r[0] for r in engineered]}")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(SQLITE_PATH)
    con.execute(DDL)
    con.executemany(
        f"INSERT INTO {TABLE} "
        "(line_id, group_label, limit_intent, limit_pct, note, owner, "
        " reviewed_on, provenance) VALUES (?,?,?,?,?,?,?,?) "
        "ON CONFLICT(line_id) DO UPDATE SET "
        "group_label=excluded.group_label, "
        "limit_intent=excluded.limit_intent, "
        "limit_pct=excluded.limit_pct, "
        "note=excluded.note, "
        "owner=excluded.owner, "
        "reviewed_on=excluded.reviewed_on, "
        "provenance=excluded.provenance",
        rows,
    )
    con.commit()

    total = con.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
    con.close()
    print(f"\n  loaded: {total} {TABLE} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
