"""Cross-store views, defined ONCE so no loader can shrink them.

## The hazard this exists to remove

`v_entity_jurisdiction` unions every table that knows an entity's
jurisdiction. Wave 13b Task 2 created it over two tables; Task 8 added a third.
When each loader carried its own `CREATE OR REPLACE VIEW`, re-running the
EARLIER loader — for any reason, on any branch — silently rebuilt the view
**without** the third source. Nothing would have failed: the view still exists,
every query still returns rows, and cross-border counts quietly drop.

That is the same shape as the `context_debt` TRUNCATE (`known-issues.md`
§12.8) and the Wave 10 person comparison (§14.3): a wave asserting ownership
over something it only partly knows about. The fix is the same — the
definition lives in one place, and it is built from **whichever tables actually
exist**, so a loader run at any point in the sequence produces a view that is
correct for that point and never one that is smaller than the data.

## Column naming

The key column is `entity_id`, not `lei`. Engineered entities have no LEI, and
a column named `lei` carrying a non-LEI identifier is a lie a downstream join
would believe.
"""

from __future__ import annotations

#: Every source of an entity jurisdiction, in load order. Each entry is
#: (table, id column, name column, jurisdiction column, country expression).
JURISDICTION_SOURCES = [
    ("legal_entity", "lei", "legal_name", "legal_jurisdiction",
     "split_part(legal_jurisdiction, '-', 1)"),
    ("registry_company", "lei", "legal_name", "legal_jurisdiction",
     "legal_country"),
    ("engineered_entity", "entity_id", "name", "jurisdiction", "jurisdiction"),
]


def existing_tables(cur, schema: str) -> set[str]:
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = %s",
        (schema,),
    )
    return {r[0] for r in cur.fetchall()}


def ensure_views(cur, schema: str) -> list[str]:
    """(Re)build the cross-store views. Returns the sources actually used.

    Safe to call from any loader at any point: sources that do not exist yet
    are skipped, and a later call that finds more of them widens the view.
    Never narrows it below what the store can support.
    """
    present = existing_tables(cur, schema)
    used = [s for s in JURISDICTION_SOURCES if s[0] in present]
    if not used:
        raise RuntimeError(
            f"no jurisdiction source table exists in {schema}; "
            f"expected at least one of "
            f"{[s[0] for s in JURISDICTION_SOURCES]}"
        )

    branches = "\n    UNION ALL\n".join(
        f"    SELECT {id_col}::text AS entity_id, {name_col} AS legal_name, "
        f"{juris_col} AS legal_jurisdiction, {country_expr} AS legal_country, "
        f"'{table}'::text AS owner_table\n      FROM \"{schema}\".{table}"
        for table, id_col, name_col, juris_col, country_expr in used
    )

    # Dropped rather than replaced: CREATE OR REPLACE cannot change a view
    # column's name or type, and both changed when `entity_id` replaced `lei`.
    cur.execute(f'DROP VIEW IF EXISTS "{schema}".v_ownership_cross_border')
    cur.execute(f'DROP VIEW IF EXISTS "{schema}".v_entity_jurisdiction')
    cur.execute(f'CREATE VIEW "{schema}".v_entity_jurisdiction AS\n{branches}')

    if "corporate_ownership_record" in present:
        cur.execute(f"""
            CREATE VIEW "{schema}".v_ownership_cross_border AS
                SELECT r.*,
                       c.legal_jurisdiction AS child_jurisdiction,
                       p.legal_jurisdiction AS parent_jurisdiction,
                       c.legal_country      AS child_country,
                       p.legal_country      AS parent_country,
                       (c.legal_country IS NOT NULL
                        AND p.legal_country IS NOT NULL
                        AND c.legal_country <> p.legal_country) AS cross_border
                  FROM "{schema}".corporate_ownership_record r
                  LEFT JOIN "{schema}".v_entity_jurisdiction c
                         ON c.entity_id = r.child_lei
                  LEFT JOIN "{schema}".v_entity_jurisdiction p
                         ON p.entity_id = r.parent_lei
        """)
    return [s[0] for s in used]
