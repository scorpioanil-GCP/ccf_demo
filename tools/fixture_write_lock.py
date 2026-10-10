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

`D-IMPL-380` (Dave, 2026-10-10 05:34 MST: *"Two separate barriers. The lock
refuses an outside dependent. cp-03 drops without CASCADE."*) adds a second
check to the same block, before any write: no object OUTSIDE the schema may
depend on any of the twelve tables — a view or materialized view (through its
``_RETURN`` rewrite rule), any other rule (named as a rule on its table, never
as a view: `D-IMPL-380` second round, ruling 4 (a)), a foreign key from a table
in another schema, or any other
normal dependency (``deptype = 'n'`` in ``pg_depend``) on a table or its row
type. The relation-name check above inspects only the schema itself, so such a
dependent passed it, and cp-03's former ``DROP TABLE ... CASCADE`` then dropped
it. The refusal names each dependent with its schema. Example-only: this lock
guards the cp-00..03 setup scripts and the harness that applies them, not the
SDK.

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
    """The `DO` block that refuses unless `schema` holds only `FIXTURE_TABLES`
    and nothing outside `schema` depends on any of them (`D-IMPL-380`)."""
    allowed = ", ".join(f"'{name}'" for name in FIXTURE_TABLES)
    return (
        "-- WRITE LOCK (D-IMPL-379): this script drops, rebuilds and deletes in\n"
        f"-- `{schema}`. It refuses unless every table and view in that schema is\n"
        "-- one the cp-00..03 setup scripts create -- a disposable test database.\n"
        "-- The curated estate holds far more, so it is refused, by name.\n"
        "-- (D-IMPL-380): it also refuses, naming each one with its schema, when\n"
        f"-- any object outside `{schema}` depends on one of those tables.\n"
        "DO $ccf_write_lock$\n"
        "DECLARE\n"
        "    stray text;\n"
        "    outside text;\n"
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
        "    SELECT string_agg(DISTINCT dependent, ', ' ORDER BY dependent) INTO outside\n"
        "      FROM (\n"
        "        SELECT CASE WHEN d.classid = 'pg_rewrite'::regclass\n"
        "                     AND r.rulename = '_RETURN'\n"
        "                    THEN format('%s %I.%I (schema %s)',\n"
        "                                CASE vc.relkind WHEN 'm' THEN 'materialized view'"
        " ELSE 'view' END,\n"
        "                                vn.nspname, vc.relname, vn.nspname)\n"
        "                    WHEN d.classid = 'pg_rewrite'::regclass\n"
        "                    THEN format('rule %I on %s %I.%I (schema %s)', r.rulename,\n"
        "                                CASE vc.relkind WHEN 'v' THEN 'view'"
        " WHEN 'm' THEN 'materialized view' ELSE 'table' END,\n"
        "                                vn.nspname, vc.relname, vn.nspname)\n"
        "                    ELSE format('%s %s (schema %s)', o.type, o.identity,"
        " coalesce(o.schema, '-'))\n"
        "               END AS dependent,\n"
        "               CASE WHEN d.classid = 'pg_rewrite'::regclass\n"
        "                    THEN vn.nspname ELSE o.schema END AS dependent_schema\n"
        "          FROM pg_class t\n"
        "          JOIN pg_namespace tn ON tn.oid = t.relnamespace\n"
        "          JOIN pg_type rt ON rt.oid = t.reltype\n"
        "          JOIN pg_depend d\n"
        "            ON d.deptype = 'n'\n"
        "           AND ((d.refclassid = 'pg_class'::regclass AND d.refobjid = t.oid)\n"
        "             OR (d.refclassid = 'pg_type'::regclass\n"
        "                 AND d.refobjid IN (rt.oid, rt.typarray)))\n"
        "          CROSS JOIN LATERAL pg_identify_object(d.classid, d.objid, d.objsubid) o\n"
        "          LEFT JOIN pg_rewrite r\n"
        "            ON d.classid = 'pg_rewrite'::regclass AND r.oid = d.objid\n"
        "          LEFT JOIN pg_class vc ON vc.oid = r.ev_class\n"
        "          LEFT JOIN pg_namespace vn ON vn.oid = vc.relnamespace\n"
        f"         WHERE tn.nspname = '{schema}'\n"
        f"           AND t.relname IN ({allowed})\n"
        "      ) dependents\n"
        f"     WHERE dependent_schema IS DISTINCT FROM '{schema}';\n"
        "    IF outside IS NOT NULL THEN\n"
        "        RAISE EXCEPTION 'D-IMPL-380 write lock: % depend on the tables of"
        " schema %, from outside it. This is not a disposable test database;"
        " refusing to write.', "
        f"outside, '{schema}';\n"
        "    END IF;\n"
        "END\n"
        "$ccf_write_lock$;\n"
    )
