#!/usr/bin/env python3
"""Wave 20 gap 1 -- jurisdiction entitlement, recomputed rather than read.

    uv run validators/entitlement.py

`counterparty-reference-snapshot` §B binds the T1 policy as *"Entitlement
scope only -- JURISDICTION VISIBILITY per calling principal"*, and §D's
Validation gates line names **suppression silence**. This module answers the
only question those two actually ask: **does the visible entity set differ
between principals, and is any principal genuinely restricted?**

## Why a column is not the answer

`ccf_v2.principal` gained a jurisdiction scope in Wave 20, and a check that
read it would be worthless. Two principals scoped to `KR` and `JP` differ in
the column and see exactly the same thing -- nothing -- because neither
jurisdiction is in the population. A gate counting distinct scope values
reports two differing principals and is wrong.

So every figure here is recomputed from `legal_entity.legal_jurisdiction`
against the scope rows at the moment the check runs. **Nothing reads a stored
visibility flag, a cached set, or a count of scope rows.**

## The floor is ours

v0.3 states no numeric requirement here. The *"3 principals with differing
jurisdiction entitlement"* figure came from the superseded Q019 form's §F --
and under v0.3, §F is *Source binding & readiness*, so citing it would be
wrong twice over. 3 is kept as **our** sufficiency bar: it is the smallest
number that shows pairwise difference is not the coincidence of two.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

#: Our own bar, not the spec's. See the module docstring.
DISTINCT_PRINCIPALS_FLOOR = 3


def in_scope(jurisdiction: str | None, prefix: str) -> bool:
    """Does `jurisdiction` fall inside the entitlement `prefix`?

    A country prefix covers its ISO 3166-2 subdivisions -- `US` admits `US-DE`
    -- because the estate holds both forms and an entitlement expressed per
    country would otherwise miss every Delaware entity in it.

    ENTITLEMENT NARROWS AND NEVER WIDENS, so the rule is asymmetric on
    purpose: `US-DE` does NOT admit `US-MD`, and `US` does not admit `DE` the
    country merely because the letters appear. The match is on the whole code
    or on a code followed by `-`, never on bare containment.
    """
    if not jurisdiction:
        return False
    j, p = jurisdiction.strip(), prefix.strip()
    return j == p or j.startswith(p + "-")


def visible(entities, prefixes) -> set[str]:
    """The LEIs a principal holding `prefixes` may see.

    `entities` is an iterable of `(lei, legal_jurisdiction)`. An empty scope
    sees nothing -- it is not shorthand for "unrestricted".
    """
    prefixes = list(prefixes)
    return {lei for lei, juris in entities
            if any(in_scope(juris, p) for p in prefixes)}


def distinct_visible_sets(sets: dict[str, set]) -> int:
    """How many genuinely different views exist across the principals.

    The number that decides the gate. Counts DISTINCT SETS, not principals and
    not scope values: two principals scoped to jurisdictions nobody loaded
    both see nothing, and that is one view, not two.
    """
    return len({frozenset(s) for s in sets.values()})


def asymmetric_pair(sets: dict[str, set]) -> tuple[str, str] | None:
    """A principal pair where the first sees an entity the second does not.

    Implied by two sets differing, but asserted explicitly because it is the
    concrete statement of suppression: some named entity is withheld from a
    named principal, which is what the operator has to be able to do.
    """
    for a, sa in sets.items():
        for b, sb in sets.items():
            if a != b and (sa - sb):
                return (a, b)
    return None


def every_principal_is_suppressed(sets: dict[str, set], total: int) -> bool:
    """Is every principal restricted, i.e. does none of them see everything?

    Distinctness alone is satisfiable while one principal is unrestricted, and
    for THAT principal the Policy Operator filters nothing. An unrestricted
    principal is a no-op hiding inside a passing check, so it fails here.

    No principals at all is not a pass: an empty estate suppresses nothing.
    """
    if not sets:
        return False
    return all(len(s) < total for s in sets.values())


# --------------------------------------------------------------------------
# live
# --------------------------------------------------------------------------

def _load():
    from ccf.config import PG_SCHEMA_V2, pg_connect
    S = PG_SCHEMA_V2
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, legal_jurisdiction FROM "{S}".legal_entity')
        entities = cur.fetchall()
        cur.execute(f'SELECT principal_id, jurisdiction_prefix '
                    f'FROM "{S}".principal_jurisdiction ORDER BY 1, 2')
        scopes: dict[str, list[str]] = {}
        for pid, prefix in cur.fetchall():
            scopes.setdefault(pid, []).append(prefix)
    return entities, scopes


def main() -> int:
    entities, scopes = _load()
    total = len(entities)
    sets = {pid: visible(entities, prefixes) for pid, prefixes in scopes.items()}

    distinct = distinct_visible_sets(sets)
    pair = asymmetric_pair(sets)
    suppressed = every_principal_is_suppressed(sets, total)

    print("JURISDICTION ENTITLEMENT — recomputed from the stores, never read\n")
    print(f"  {total} entities, {len(sets)} principals with a scope\n")
    for pid in sorted(sets):
        print(f"  {pid:14s} {len(sets[pid]):3d} of {total} visible"
              f"   scope: {', '.join(scopes[pid])}")

    ok = True
    print()
    if distinct >= DISTINCT_PRINCIPALS_FLOOR:
        print(f"  [PASS] {distinct} distinct visible sets "
              f"(floor {DISTINCT_PRINCIPALS_FLOOR}, ours not the spec's)")
    else:
        ok = False
        print(f"  [FAIL] only {distinct} distinct visible sets — the Policy "
              f"Operator cannot be shown to filter")
    if pair:
        a, b = pair
        example = sorted(sets[a] - sets[b])[0]
        print(f"  [PASS] {a} sees {example}, {b} does not")
    else:
        ok = False
        print("  [FAIL] no entity is visible to one principal and not another")
    if suppressed:
        print(f"  [PASS] every principal is restricted — none sees all {total}")
    else:
        ok = False
        unrestricted = [p for p, s in sets.items() if len(s) >= total]
        print(f"  [FAIL] unrestricted principals: {unrestricted or '(none — no principals)'}")

    print("\n  Every figure recomputed from legal_entity.legal_jurisdiction "
          "against\n  principal_jurisdiction. No stored visibility flag is read.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
