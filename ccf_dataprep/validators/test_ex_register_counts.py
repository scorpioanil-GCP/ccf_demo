"""The register checker must not quietly stop checking things.

This file exists because the checker it guards has had the same defect twice,
in opposite directions, and both times it was silent:

  v1  required a BARE integer in the Assertions cell. Labelling two rows
      `**261 assertions · 255 subjects**` removed them from the DENOMINATOR --
      "18 of 80" became "16 of 78", which reads as progress while the checker
      had stopped looking at them. Caught by the vault re-running it, not here.

  v2  captured the fourth cell whatever it held and took its first integer.
      That pulled in 85 rows from the register's OTHER table shape -- four
      columns, no Assertions -- and read their RATIONALE as a count, inventing
      52 disagreements including `effectiveDate doc 166479 live 6`.

Both are one defect: **a check whose population is not its question.** The
question is "does the Assertions column still describe the ledger", so the
population is exactly the rows under a header that HAS an Assertions column.

The tests below pin that population and prove the parser discriminates. They
deliberately do NOT pin the number of disagreements -- that number is supposed
to move, because the ledger is append-only and every wave loads more.
"""

from __future__ import annotations

import validators.ex_register_counts as erc

#: Rows under an Assertions header, measured 2026-09-12. This may legitimately
#: GROW when a wave adds terms. It must never shrink silently -- a drop means
#: rows left the checker, which is exactly how v1 failed.
MIN_CHECKABLE_ROWS = 88


def test_the_checkable_population_has_not_shrunk() -> None:
    rows = erc.check()
    assert len(rows) >= MIN_CHECKABLE_ROWS, (
        f"the checker now sees {len(rows)} rows, was {MIN_CHECKABLE_ROWS}. "
        f"Rows have LEFT the population -- they are not passing, they are not "
        f"being checked. Usually an Assertions cell was reformatted into "
        f"something `claimed_count` cannot read. Widen the parser; do not "
        f"lower this number.")


def test_no_row_is_unparseable() -> None:
    """A cell the checker cannot read must be loud, and there should be none."""
    unreadable = [r[0] for r in erc.check() if r[3] is None]
    assert not unreadable, (
        f"Assertions cells with no integer: {unreadable}. These are reported "
        f"as UNPARSEABLE rather than dropped, but they are still unchecked.")


def test_claimed_count_reads_every_label_shape_in_use() -> None:
    """POSITIVE control on the parser, one case per shape the register uses."""
    assert erc.claimed_count(" 43 ") == 43
    assert erc.claimed_count(" **87, not 85** ") == 87
    assert erc.claimed_count(" **261 assertions · 255 subjects** (measured 2026-09-12) ") == 261
    assert erc.claimed_count(" 12 (10 subjects) ") == 12
    # Comma-formatted. NONE of the original five tests used a four-digit count,
    # which is why every one of them stayed green while `2,890` parsed as `2`.
    assert erc.claimed_count(" 2,890 ") == 2890
    assert erc.claimed_count(" 1,265 ") == 1265
    assert erc.claimed_count(" 3,022 (re-measured 2026-08-26, was 1,724) ") == 3022
    assert erc.claimed_count(" 7,736 edges (3,868 unordered pairs) ") == 7736
    # ... and the comma that must NOT extend the match, which is why the
    # pattern requires exactly three digits after it.
    assert erc.claimed_count(" **87, not 85** ") == 87


def test_claimed_count_returns_none_rather_than_guessing() -> None:
    """NEGATIVE control: a cell with no integer must not invent one."""
    assert erc.claimed_count(" no FIBO role class for this ") is None
    assert erc.claimed_count("") is None


def test_four_column_tables_are_excluded_from_the_population() -> None:
    """The v2 failure: rationale cells read as counts.

    `ex:Banker` lives in a four-column table with no Assertions column. It must
    not appear in the checked population at all -- not as a pass, not as a
    disagreement, not as unparseable.
    """
    names = {r[0] for r in erc.check()}
    assert "Banker" not in names, (
        "a row from a four-column table entered the population; its rationale "
        "cell will be read as a count")
    # ... and the positive half: a row that IS under an Assertions header is in.
    assert "startOffset" in names, (
        "startOffset is under an Assertions header and must be checked")
