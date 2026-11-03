"""Every store in the catalog's partition table must name its own LEVEL.

The defect this guards against: the Store column once carried four bare
identifiers -- `fibo-v2`, `ccf_v2`, `fibo_v2`, `data/departmental.sqlite` --
which are a ledger, a schema, a database and a file path, with nothing saying
which was which. Two of them differ by one character. A reader takes `ccf_v2`
for a database name and fails to connect, and the catalog is mirrored into the
vault, so the ambiguity travels.

The check is on the GENERATED artifact, not on the generator's source, because
what downstream reads is the artifact.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ccf.config import PG  # noqa: E402

CATALOG = REPO_ROOT / "docs" / "store-catalog.md"

# A level word answers "what kind of thing is this name?" -- the question a
# bare identifier leaves open.
LEVEL_WORDS = ("ledger", "schema", "database", "file")

EXPECTED_STORES = {"Fluree", "Postgres", "MongoDB", "SQLite", "Neo4j"}


def parse_partition_rows(markdown: str) -> dict[str, str]:
    """Return {store name: address cell} for the partition table.

    Raises AssertionError when the table has no Address column at all -- the
    regression where the whole column is dropped by a hand edit or by a
    renderer change.
    """
    lines = markdown.splitlines()
    try:
        head = next(i for i, ln in enumerate(lines)
                    if ln.startswith("| Store |"))
    except StopIteration:  # pragma: no cover - guarded by the tests below
        raise AssertionError("no partition table found in the catalog")

    cols = [c.strip() for c in lines[head].strip("|").split("|")]
    assert "Address" in cols, (
        f"partition table has no Address column; columns are {cols}. "
        "A bare identifier there reads as a database name.")
    addr_ix = cols.index("Address")

    rows: dict[str, str] = {}
    for ln in lines[head + 2:]:
        if not ln.startswith("|"):
            break
        cells = [c.strip() for c in ln.strip("|").split("|")]
        store = re.sub(r"[*`]", "", cells[0]).strip()
        rows[store] = cells[addr_ix]
    return rows


def address_defects(rows: dict[str, str]) -> list[str]:
    """Every address must open with a level word and carry an identifier."""
    bad = []
    for store, addr in rows.items():
        first = addr.split()[0].lower() if addr else ""
        if first not in LEVEL_WORDS:
            bad.append(f"{store}: {addr!r} does not begin with a level word")
        elif "`" not in addr:
            bad.append(f"{store}: {addr!r} names a level but no identifier")
    return bad


@pytest.fixture(scope="module")
def rows() -> dict[str, str]:
    assert CATALOG.exists(), f"{CATALOG} missing -- run the generator"
    return parse_partition_rows(CATALOG.read_text())


def test_every_store_is_present(rows):
    assert set(rows) == EXPECTED_STORES, (
        f"partition table lists {sorted(rows)}, expected "
        f"{sorted(EXPECTED_STORES)}")


def test_every_address_names_its_level(rows):
    assert address_defects(rows) == []


def test_postgres_names_the_database_not_only_the_schema(rows):
    addr = rows["Postgres"]
    assert "schema" in addr.lower(), (
        f"Postgres address {addr!r} must say the word 'schema' -- ccf_v2 is a "
        "schema, and a reader who takes it for a database cannot connect")
    assert f"`{PG['dbname']}`" in addr, (
        f"Postgres address {addr!r} does not name the database "
        f"{PG['dbname']!r} from ccf.config; a reader cannot learn it from "
        "the catalog at all")


# --- positive controls ----------------------------------------------------
# Without these the checks above could pass on any input and nobody would know.

BROKEN_BARE_IDENTIFIERS = """
| Store | Owns | Scale |
|---|---|---|
| **Fluree** `fibo-v2` | R | 1 |
| **Postgres** `ccf_v2` | E | 2 |
"""

BROKEN_LEVEL_DROPPED = """
| Store | Address | Owns | Scale |
|---|---|---|---|
| **Fluree** | ledger `fibo-v2` | R | 1 |
| **Postgres** | `ccf_v2` | E | 2 |
"""


def test_control_rejects_a_table_with_no_address_column():
    with pytest.raises(AssertionError, match="no Address column"):
        parse_partition_rows(BROKEN_BARE_IDENTIFIERS)


def test_control_rejects_an_address_missing_its_level_word():
    defects = address_defects(parse_partition_rows(BROKEN_LEVEL_DROPPED))
    assert len(defects) == 1 and "Postgres" in defects[0], defects
