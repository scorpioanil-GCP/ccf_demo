#!/usr/bin/env python3
"""Dump the Fluree ledger's current state to N-Triples, and restore it.

Fluree 4.1.4 exposes no backup, snapshot, export or dump endpoint -- all four
paths return 404 -- so a backup has to be taken through the query API. That is
workable here because the ledger is small (63,973 triples as of t=1421) and,
crucially, because **every literal in it is a plain string**: 27,607 of 27,607
carry no datatype, so nothing is lost in serialisation.

That last point was measured, not assumed, and it matters in both directions:

    Fluree 4.1.4 CORRUPTS xsd:date literals on write. Inserting
    "2026-01-02"^^xsd:date and reading it back returns 1972-01-01, and
    successive inserts return values climbing about two days apiece
    (2014-03-28, 2014-03-30, 2014-04-01) -- a transaction-derived number, not
    the date. The same values written as plain strings round-trip exactly.

The estate is unaffected because it already stores dates as strings
(`ex:validFrom "2024-12-19"`). The hazard is prospective: anyone "improving" a
loader by adding datatypes would silently destroy every date. This dump would
also mis-restore such a value, and says so rather than pretending otherwise --
`--check` fails loudly if a typed literal ever appears.

A dump is NOT a point-in-time snapshot of history. Fluree is append-only, so
history is preserved in the ledger regardless; what this captures is the
CURRENT STATE, which is what a restore needs.

    uv run loaders/dump_fluree.py                       # dump to backups/
    uv run loaders/dump_fluree.py --check               # verify a dump reads back
    uv run loaders/dump_fluree.py --restore <file> --dry-run
    uv run loaders/dump_fluree.py --restore <file>      # re-assert into the ledger

Restore is additive: it INSERTs every triple in the file. It does not retract
whatever the ledger has gained since, because a restore that deleted unknown
triples would be a far more dangerous operation than the one it protects
against. To roll back a specific change, restore the dump and retract the
change's own triples.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from ccf import fluree
from ccf.config import FLUREE_LEDGER_V2 as L
from ccf.config import REPO_ROOT

BACKUPS = REPO_ROOT / "backups"
BATCH = 500

#: N-Triples literal escaping, per the spec: backslash first, then quote, then
#: the three control characters that may not appear raw.
_ESCAPES = [("\\", "\\\\"), ('"', '\\"'), ("\n", "\\n"), ("\r", "\\r"),
            ("\t", "\\t")]


def nt_literal(value: str, datatype: str | None, lang: str | None) -> str:
    for a, b in _ESCAPES:
        value = value.replace(a, b)
    out = f'"{value}"'
    if lang:
        return f"{out}@{lang}"
    if datatype:
        return f"{out}^^<{datatype}>"
    return out


def nt_term(term: dict) -> str:
    if term["type"] == "uri":
        return f"<{term['value']}>"
    if term["type"] == "bnode":
        return f"_:{term['value']}"
    return nt_literal(term["value"], term.get("datatype"),
                      term.get("xml:lang"))


def read_state() -> list[dict]:
    r = fluree.query(f"SELECT ?s ?p ?o FROM <{L}> WHERE {{ ?s ?p ?o }}")
    return r["results"]["bindings"]


def serialise(rows: list[dict]) -> list[str]:
    return [f"{nt_term(b['s'])} {nt_term(b['p'])} {nt_term(b['o'])} ."
            for b in rows]


#: One N-Triples line. Deliberately strict: a line this does not match is
#: reported rather than skipped, because a restore that silently drops
#: unparseable lines restores less than it claims.
LINE = re.compile(
    r'^(<[^>]*>|_:\S+)\s+(<[^>]*>)\s+(<[^>]*>|_:\S+|".*")\s*\.\s*$')


def dump(path: Path | None) -> int:
    t = fluree.ledger_t()
    rows = read_state()
    typed = [b for b in rows
             if b["o"]["type"] == "literal" and b["o"].get("datatype")]
    lines = serialise(rows)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    path = path or (BACKUPS / f"fibo-v2-t{t}-{stamp}.nt")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")

    counted = fluree.count_triples()
    print(f"  ledger {L} at t={t}")
    print(f"  {len(lines):,} triples written  (COUNT(*) says {counted:,})")
    print(f"  typed literals: {len(typed)}"
          + ("" if not typed else "  <-- see the xsd:date warning in this file"))
    print(f"  {path}")
    if len(lines) != counted:
        print("  MISMATCH — the dump is short. Do not rely on it.")
        return 1
    if typed:
        print("  WARNING — typed literals present; xsd:date will not restore "
              "faithfully on Fluree 4.1.4.")
        return 1
    return 0


def check(path: Path) -> int:
    """Re-read a dump and compare it, as a SET, with the live ledger.

    Compares content rather than line counts: a dump with the right number of
    wrong lines is exactly what a count-based check cannot see.
    """
    text = path.read_text().splitlines()
    parsed, bad = set(), []
    for line in text:
        if not line.strip():
            continue
        if not LINE.match(line):
            bad.append(line)
            continue
        parsed.add(line.strip())
    live = set(serialise(read_state()))

    print(f"  file   {len(parsed):,} triples  ({len(bad)} unparseable)")
    print(f"  ledger {len(live):,} triples")
    only_file = parsed - live
    only_live = live - parsed
    print(f"  in file but not ledger : {len(only_file)}")
    print(f"  in ledger but not file : {len(only_live)}")
    for line in list(only_live)[:3]:
        print(f"      {line[:110]}")
    if bad:
        print(f"  UNPARSEABLE lines, first 3:")
        for line in bad[:3]:
            print(f"      {line[:110]}")
    ok = not bad and not only_file and not only_live
    print(f"\n  dump matches the ledger exactly: {ok}")
    return 0 if ok else 1


def restore(path: Path, dry_run: bool) -> int:
    lines = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
    bad = [ln for ln in lines if not LINE.match(ln)]
    if bad:
        print(f"  {len(bad)} unparseable lines — refusing to restore a file "
              f"this cannot read in full.")
        for ln in bad[:3]:
            print(f"      {ln[:110]}")
        return 1

    live = set(serialise(read_state()))
    missing = [ln for ln in lines if ln not in live]
    print(f"  file {len(lines):,} triples · ledger already holds "
          f"{len(lines) - len(missing):,} · {len(missing):,} to assert")
    if dry_run:
        print("\n  DRY RUN — nothing written.")
        for ln in missing[:3]:
            print(f"      + {ln[:110]}")
        return 0
    if not missing:
        print("  nothing to do.")
        return 0
    for i in range(0, len(missing), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(missing[i:i + BATCH]) + "\n}")
        print(f"    {min(i + BATCH, len(missing)):>6}/{len(missing)}")
    print(f"\n  restored. ledger t={fluree.ledger_t()}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, help="dump destination")
    ap.add_argument("--check", type=Path, nargs="?", const=Path("LATEST"),
                    help="verify a dump against the live ledger")
    ap.add_argument("--restore", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print(f"Fluree dump — {L}\n")
    if args.restore:
        return restore(args.restore, args.dry_run)
    if args.check:
        path = args.check
        if str(path) == "LATEST":
            files = sorted(BACKUPS.glob("fibo-v2-*.nt"))
            if not files:
                print("  no dumps in backups/")
                return 1
            path = files[-1]
            print(f"  checking {path.name}")
        return check(path)
    return dump(args.out)


if __name__ == "__main__":
    sys.exit(main())
