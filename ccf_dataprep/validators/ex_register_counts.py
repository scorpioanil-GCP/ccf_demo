#!/usr/bin/env python3
"""Does the `ex:` register's Assertions column still describe the ledger?

`docs/ccf_dataprep_v2.md` states, of these figures:

    All figures below were read back from the loaded ledger, not predicted
    from the generator.

That makes each one a **measurement**, and a measurement frozen into a document
decays. The doc already records the shape of the decay once, against
`thresholdComponent`: a cell "correct before Task 10's engineered amendment
added a tenth subject" that "went stale when the column was updated and the
prose was not."

Nothing recomputed the rest. `validators/binding_drift.py` is the near
neighbour and does NOT cover this: it compares what the **vault** publishes
against the estate, so a wrong number in our own table stays invisible until
it is mirrored. This closes that half.

## Why it matters more than a wrong number

The table is mirrored to `wiki/context-products/content/fibo-iri-binding`, and
the CCF SDK reads it to decide what to bind against. **The mirror does not
parrot this file** — vault `Q042` established that it was measured separately,
so a stale row here does not automatically become a stale row there, and five
mirror cells held a number appearing in neither document. Per `Q042` the
precedence rule is now split: the repository wins on BINDINGS, but for COUNTS
the ledger wins and neither document is authoritative. A count that understates
tells a consumer a predicate is rarer than it is; `ex:amendmentAction`
published 85 against a live 87 because two amendments carry two actions each,
and a consumer assuming one-per-subject drops half of each. That is the same
defect class as `thresholdComponent` above, and as the composite thresholds in
Wave 14 — **counting the wrong unit**, not miscounting.

Run: uv run validators/ex_register_counts.py
     uv run validators/ex_register_counts.py --wave 21   # one section only
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ccf import config as C  # noqa: E402
from ccf import fluree  # noqa: E402

DOC = Path(__file__).resolve().parent.parent / "docs" / "ccf_dataprep_v2.md"

#: The register uses TWO table shapes and only one has an Assertions column:
#:
#:   | Local name | Kind | Full IRI | Assertions | Why not FIBO |   <- checkable
#:   | Local name | Kind | Full IRI | Why not FIBO |                <- no count
#:
#: So the population is decided by the HEADER, not by a row regex. Two earlier
#: versions got this wrong in opposite directions and both were silent:
#:
#:   v1 required a bare integer in cell 4 and skipped everything else. Labelling
#:      two rows `**261 assertions · 255 subjects**` dropped them from the
#:      DENOMINATOR -- 18 of 80 became 16 of 78, which reads as progress while
#:      the checker stopped looking.
#:   v2 captured cell 4 whatever it held and took its first integer. That pulled
#:      in 85 rows from the 4-column tables and read their RATIONALE as a count,
#:      inventing 52 disagreements including `effectiveDate doc 166479 live 6`.
#:
#: A checker's population must be its question. Here the question is "does the
#: Assertions column still describe the ledger", so the population is exactly
#: the rows under a header that HAS one, and a cell in such a table that holds
#: no integer is UNPARSEABLE and reported loudly -- never dropped.
HEADER = re.compile(r"^\|\s*Local name\s*\|(.+)\|\s*$", re.M)
ROW = re.compile(
    r"^\|\s*`([A-Za-z][A-Za-z0-9_]*)`\s*\|\s*(class|property)\s*\|\s*"
    r"`(http://example\.org/fibo/[^`]+)`\s*\|([^|]*)\|",
    re.M)

#: Any term row, whatever table it sits in — used to report how many rows the
#: register holds in total, so a shrinking checkable population is visible.
TERM_ROW = ROW

#: First figure in an Assertions cell, THOUSANDS SEPARATOR INCLUDED.
#: Shapes in use: `43` · `**87, not 85**` · `261 assertions · 255 subjects` ·
#: `12 (10 subjects)` · `2,890` · `7,736 edges (3,868 unordered pairs)`.
#:
#: `\d+` alone was wrong and wrong CONFIDENTLY: it read `2,890` as `2` and
#: `1,265` as `1`, reporting two already-correct rows as drifted by a factor of
#: a thousand. `test_no_row_is_unparseable` stayed green throughout, because
#: `2,890` does parse -- to `2`. A guard against a cell it cannot read cannot
#: catch a cell it reads wrongly, and a wrong number is worse than an
#: unreadable one because someone acts on it.
#:
#: The original pattern was deliberately comma-TOLERANT so that `**87, not 85**`
#: yielded 87. That tolerance is exactly what truncated `2,890`. It was not
#: missing a case; it was succeeding at the wrong one.
#:
#: `(?:,\d{3})*` requires a comma followed immediately by three digits, so
#: `", not"` still terminates the match at 87 while `,890` extends it.
_FIRST_INT = re.compile(r"\d+(?:,\d{3})*")


def claimed_count(cell: str) -> int | None:
    m = _FIRST_INT.search(cell)
    return int(m.group(0).replace(",", "")) if m else None


def _checkable_spans(text: str) -> list[tuple[int, int]]:
    """Character ranges of tables whose header carries an Assertions column."""
    heads = list(HEADER.finditer(text))
    spans = []
    for n, h in enumerate(heads):
        if "Assertions" not in h.group(1):
            continue
        end = heads[n + 1].start() if n + 1 < len(heads) else len(text)
        spans.append((h.end(), end))
    return spans


#: `#### Wave N ...` headings, so a run can be scoped to one section.
HEADING = re.compile(r"^#### Wave (\d+)[^\n]*$", re.M)


def _section_of(text: str, pos: int) -> str | None:
    last = None
    for m in HEADING.finditer(text):
        if m.start() > pos:
            break
        last = m.group(1)
    return last


def live_count(iri: str, kind: str) -> int:
    q = (f'SELECT ?s FROM <{C.FLUREE_LEDGER_V2}> WHERE {{ ?s a <{iri}> }}'
         if kind == "class" else
         f'SELECT ?s ?o FROM <{C.FLUREE_LEDGER_V2}> WHERE {{ ?s <{iri}> ?o }}')
    # Counted client-side: Fluree's COUNT(*) under-reports on multi-pattern
    # clauses (known-issues.md §60), and this file exists to check arithmetic.
    return len(fluree.query(q)["results"]["bindings"])


def check(wave: str | None = None) -> list[tuple]:
    """Rows under an Assertions header, with their claimed count."""
    text = DOC.read_text()
    spans = _checkable_spans(text)
    out = []
    for m in ROW.finditer(text):
        if not any(a <= m.start() < b for a, b in spans):
            continue                      # 4-column table: no count to check
        term, kind, iri, cell = m.groups()
        sect = _section_of(text, m.start())
        if wave and sect != wave:
            continue
        out.append((term, kind, sect, claimed_count(cell), live_count(iri, kind)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wave", help="only rows under '#### Wave N'")
    args = ap.parse_args()

    rows = check(args.wave)
    if not rows:
        print("no machine-readable rows matched -- check the table format "
              "before trusting this as a pass")
        return 1

    unparseable = [r for r in rows if r[3] is None]
    bad = [r for r in rows if r[3] is not None and r[3] != r[4]]

    # Louder than a disagreement, and first: a row nobody can read is a row
    # nobody is checking.
    for term, _kind, sect, _c, live in unparseable:
        print(f"  UNPARSEABLE  Wave {sect or '?':>3}  {term:22} "
              f"(live {live}) -- Assertions cell holds no integer")
    for term, _kind, sect, claimed, live in sorted(bad, key=lambda r: -abs(r[4] - r[3])):
        print(f"  Wave {sect or '?':>3}  {term:22} doc {claimed:>5}  "
              f"live {live:>5}  ({live - claimed:+d})")
    print(f"\n  {len(bad)} of {len(rows)} term rows disagree with "
          f"{C.FLUREE_LEDGER_V2}"
          + (f"; {len(unparseable)} UNPARSEABLE" if unparseable else ""))
    if bad:
        print("  A stale count is a claim about the estate that the estate "
              "no longer supports.")
        print("  NOTE: these do NOT automatically reach the SDK. The vault "
              "mirror was\n  measured separately, not copied -- on 2026-09-12 "
              "12 of 18 mirror cells\n  already held the live value and five "
              "held a THIRD number, in neither\n  this file nor the ledger "
              "(vault Q042). Two documents describing one\n  append-only "
              "ledger drift independently. Per Q042 the precedence rule is\n"
              "  now split: the repository wins on BINDINGS, but for COUNTS "
              "the ledger\n  wins and neither document is authoritative -- "
              "re-measure with this tool.")
    return 1 if (bad or unparseable) else 0


if __name__ == "__main__":
    raise SystemExit(main())


# --------------------------------------------------------------------------
# prose-vs-table: the defect ccf-sdk caught on 2026-09-10
# --------------------------------------------------------------------------

#: ONLY the mirror-scoping sentence — "These <N> terms are new since the last
#: mirror refresh". Deliberately NOT any "<N> terms" phrase: an earlier version
#: matched every one, and of 12 hits exactly one was real. Wave 16's "nine
#: terms this repo already binds" is about FIBO Provisional modules, not about
#: its own table; Wave 18's "four ... two ... five" name subsets. A guard whose
#: hits are 1-in-12 real trains the reader to skip it, which is worse than not
#: having it. This sentence is the one the CUSTODIAN scopes the refresh from,
#: so it is the one whose arithmetic has consequences.
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
         "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
         "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15}
PROSE = re.compile(
    r"\*{0,2}(" + "|".join(WORDS) + r")\*{0,2}\s+terms are new since the last"
    r"\s+mirror refresh", re.I)


def prose_vs_table() -> tuple[list, list]:
    """Stated term-counts that disagree with their own table.

    Returns `(disagreements, skipped)`.

    The Wave 21 section said "Twelve `ex:` terms" at the top and "These seven
    terms are new" at the bottom, because the table grew from 7 rows to 12 and
    only the opening sentence was updated. The table was right both times.

    That matters more than a typo: the custodian scopes the vault mirror
    refresh from that prose. Seven terms would have been mirrored and five
    silently not -- and a term missing from the mirror is one the SDK cannot
    bind against, with nothing anywhere reporting it absent.

    ## Only unambiguous sections are judged

    A section whose prose states SEVERAL DIFFERENT counts is describing
    subsets ("four terms for X ... five for Y"), not restating a total, and
    comparing any of them against the section's whole row count is
    meaningless. The first version of this check did exactly that and reported
    12 disagreements, of which one was real -- a ratio that trains a reader to
    ignore it.

    So: unanimous prose is CHECKED, divided prose is SKIPPED AND REPORTED.
    A skip is a known blind spot, not a pass.
    """
    text = DOC.read_text()
    heads = list(HEADING.finditer(text))
    bad, skipped = [], []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[h.start():end]
        rows = len(TERM_ROW.findall(body))
        if not rows:
            continue
        claims = [(m.group(0).strip(), WORDS[m.group(1).lower()])
                  for m in PROSE.finditer(body)]
        if not claims:
            continue
        stated = {n for _, n in claims}
        if len(stated) > 1:
            skipped.append((h.group(1), sorted(stated), rows))
            continue
        n = stated.pop()
        if n != rows:
            bad.append((h.group(1), claims[0][0], n, rows))
    return bad, skipped
