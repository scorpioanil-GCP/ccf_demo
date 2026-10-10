"""The write lock that opens each cp-00…03 setup script — one authority for its text.

`D-IMPL-379` option (b), Dave 2026-10-10 00:16 MST. The eight
`tests/examples/fixtures/cp_0[0-3]_*_{schema,rows}.sql` files drop, rebuild and
delete inside `ccf_v2`, the schema name the curated estate on `192.168.4.76`
also uses. Run against that estate — as they were on 2026-09-08 and 2026-09-22 —
they rebuilt eight of its tables without keys or defaults. The pytest session
fence keeps a test run off a curated host; this lock is the second barrier,
inside the files, so any other path that applies them refuses too.

The rule is a property of the TARGET, not of how it was reached: the files may
write only into a schema that holds nothing but the twelve tables they
themselves create. A disposable test database satisfies that at every point of
a seeding run (cp-01's script finds cp-00's tables, and so on); the real estate,
with over a hundred relations, never does. The refusal names every stray
relation, so an operator reads at once which database they pointed at.

The eight committed files carry ``write_lock("ccf_v2")`` verbatim as their first
statement, and `tools/dump_cp03_fixture.py` emits the same text when it
regenerates two of them; `tests/examples/test_fixture_write_lock.py` holds both
to it.
"""

from __future__ import annotations

#: Every table any of the eight files creates. A file that creates a new one
#: must add it here, or the next file in a seeding run refuses the database.
FIXTURE_TABLES: tuple[str, ...] = (
    "crosswalk",
    "debt_reconciliation",
    "facility",
    "filing_profile",
    "financial_fact",
    "institutional_holder",
    "internal_client",
    "legal_entity",
    "peer_entity",
    "peer_fact",
    "principal",
    "principal_jurisdiction",
)


def write_lock(schema: str) -> str:
    """The `DO` block that refuses unless `schema` holds only `FIXTURE_TABLES`."""
    allowed = ", ".join(f"'{name}'" for name in FIXTURE_TABLES)
    return (
        "-- WRITE LOCK (D-IMPL-379): this script drops, rebuilds and deletes in\n"
        f"-- `{schema}`. It refuses unless every table and view in that schema is\n"
        "-- one the cp-00..03 setup scripts create -- a disposable test database.\n"
        "-- The curated estate holds far more, so it is refused, by name.\n"
        "DO $ccf_write_lock$\n"
        "DECLARE\n"
        "    stray text;\n"
        "BEGIN\n"
        "    SELECT string_agg(c.relname, ', ' ORDER BY c.relname) INTO stray\n"
        "      FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace\n"
        f"     WHERE n.nspname = '{schema}'\n"
        "       AND c.relkind IN ('r', 'p', 'v', 'm', 'f')\n"
        f"       AND c.relname NOT IN ({allowed});\n"
        "    IF stray IS NOT NULL THEN\n"
        "        RAISE EXCEPTION 'D-IMPL-379 write lock: schema % holds %, which no"
        " cp-00..03 setup script creates. This is not a disposable test database;"
        " refusing to write.', "
        f"'{schema}', stray;\n"
        "    END IF;\n"
        "END\n"
        "$ccf_write_lock$;\n"
    )
