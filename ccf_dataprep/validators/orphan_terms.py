#!/usr/bin/env python3
"""Every `ex:` term the estate asserts must have a writer in this repository.

Fluree is an append-only ledger and the loaders upsert rather than replace. So
when a loader stops writing a predicate — the line is deleted, renamed, or
rewritten — the triples it already wrote do not disappear. They stop being
refreshed and stay in the ledger forever, indistinguishable from live data.

The estate then holds something a rebuild from an empty ledger cannot produce.
That is worse than it sounds:

  * The term looks live to every query and to every audit that counts rows.
  * It is a candidate for the binding contract, so it can be published to the
    downstream consumer as vocabulary — and then vanish on the next rebuild.
  * `validators/artifact_reproduces_store.py` cannot see it. That validator
    compares generated artifacts against Postgres TABLES; a Fluree predicate
    with no writer is outside its reach entirely.

Found 2026-08-21 (Wave 11c) while writing binding rows for the 45 unbound
terms: `ex:schemaNote` (9 assertions) and `ex:effectiveDateNote` (25) had no
writer anywhere in the repo. Both were restored rather than deleted, and this
validator exists so the next one is caught by a run instead of by someone
happening to grep for it.

Detection is source-level on purpose. The question is not "does some file
mention this word" — it is "does some file ASSERT this IRI", so the patterns
below match the three forms a loader can name a term in:

    ex:localName          a literal compact IRI in a Turtle/SPARQL string
    f"{EX}localName"      the f-string form every Python loader uses
    {EX}localName         the same, inside a larger f-string

A term named only in prose, a comment, or a frozen debt list does not count as
a writer — that is the distinction the Wave 11b binding verifier learned the
hard way, three times, by matching against raw document text.

Read-only.

    uv run validators/orphan_terms.py
    uv run validators/orphan_terms.py --json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

from ccf.config import EX, REPO_ROOT

#: Directories searched for a writer. `docs/` is deliberately absent: a term
#: documented but never asserted is a different problem (an unused binding
#: row), and prose is exactly what must NOT count as evidence here.
SOURCE_DIRS = ("loaders", "generators", "validators", "ccf")

#: Files excluded from the writer search because they name `ex:` terms as
#: DATA rather than asserting them — a frozen debt list, an allowlist, or
#: this validator's own docstring. Counting these as writers would make the
#: check vacuous: every term is named in the list of terms.
NOT_WRITERS = (
    "generators/verify_fibo_wave11b_confirm.py",  # KNOWN_UNBOUND freeze list
    "validators/orphan_terms.py",                 # this file
)


def writer_patterns(local: str) -> re.Pattern:
    """Match the three ways a loader can assert `ex:<local>`."""
    esc = re.escape(local)
    return re.compile(rf"(?:ex:{esc}\b|\{{EX\}}{esc}\b)")


def source_text() -> str:
    parts = []
    for d in SOURCE_DIRS:
        for path in sorted((REPO_ROOT / d).rglob("*.py")):
            rel = path.relative_to(REPO_ROOT).as_posix()
            if rel in NOT_WRITERS:
                continue
            parts.append(path.read_text())
    return "\n".join(parts)


def find_orphans() -> list[dict]:
    # Imported here, not at module scope: this pulls in the Fluree client and
    # the import cost is real. Keeps `--help` instant.
    from generators.verify_fibo_wave11b_confirm import (estate_ex_terms,
                                                        materialised)

    src = source_text()
    classes, preds = estate_ex_terms()
    orphans = []
    for iri in sorted(classes | preds):
        local = iri.rsplit("/", 1)[-1]
        if writer_patterns(local).search(src):
            continue
        kind = "class" if iri in classes else "property"
        orphans.append({
            "term": f"ex:{local}",
            "iri": iri,
            "kind": kind,
            "assertions": materialised(iri, "class" if kind == "class" else "prop"),
        })
    return orphans, len(classes | preds)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    orphans, total = find_orphans()

    if args.json:
        print(json.dumps({"total_ex_terms": total, "orphans": orphans}, indent=2))
        return 1 if orphans else 0

    print("\nORPHANED ex: TERMS — asserted in Fluree, written by nothing in this repo\n")
    for o in orphans:
        print(f"  [FAIL] {o['term']:<28} {o['kind']:<8} {o['assertions']} assertion(s)")
        print(f"         {o['iri']}")
    if not orphans:
        print("  [ok  ] every asserted ex: term has a writer\n")

    print(f"  {total - len(orphans)}/{total} ex: terms are reproducible from source\n")
    if orphans:
        print("  An orphan is ledger residue: a loader stopped writing the term and")
        print("  the triples stayed. Decide deliberately — restore the writer, or")
        print("  retract the triples. Do NOT bind an orphan into the contract: that")
        print("  publishes vocabulary a rebuild cannot produce.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
