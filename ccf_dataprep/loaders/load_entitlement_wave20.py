#!/usr/bin/env python3
"""Wave 20 gap 1 -- jurisdiction entitlement scope per calling principal.

    uv run loaders/load_entitlement_wave20.py

`counterparty-reference-snapshot` §B binds the T1 policy as *"Entitlement
scope only -- JURISDICTION VISIBILITY per calling principal"*. `ccf_v2.principal`
carried side, perspective, sees_mnpi, sees_need_to_know and
sees_eu_person_data, and NO JURISDICTION AT ALL, so the Policy Operator had
nothing to filter on and was the no-op §D's suppression-silence gate exists to
prevent -- in the product every other product inherits its contract machinery
from.

## Why a table and not a column

Entitlement is a set, and a set in a column is either an array nobody can
constrain or a delimited string nobody can join. `principal_jurisdiction` is
one row per (principal, prefix), which joins and which a reviewer can read.

## The scopes, and why these

Chosen against the real distribution of `legal_entity.legal_jurisdiction` so
that no principal is scoped to a jurisdiction the estate does not hold -- a
scope nobody can see through is indistinguishable from no scope at all, and
would make the gate pass while proving nothing.

    PRIN-COV-001  coverage banker    US                 74 of 156
    PRIN-RES-002  research analyst   US, GB, CA        102 of 156
    PRIN-TRD-003  trader             GB, HK, SG, JP     21 of 156
    PRIN-KYC-004  EU KYC analyst     AT BE DE ES HU
                                     IT LU NL SE        21 of 156

GB is deliberately absent from the EU analyst's scope. It is the correct
post-Brexit answer and it keeps that scope from being "Europe, roughly".

**The trader and the EU analyst both see 21 entities and see COMPLETELY
DIFFERENT ONES.** That is not a coincidence to tidy away -- it is a live
falsifier sitting in the estate. A gate that compared how MANY entities each
principal can see would call those two principals identical and report three
distinct views where there are four. `validators/entitlement.py` compares
SETS, and the arms in `test_entitlement.py` fail any implementation that
counts instead.

## Provenance

`synthetic — internal`. Entitlements are bank-internal by nature -- CLAUDE.md
rule 1 names them in that class explicitly. Nothing here is fetched, and
nothing here is engineered to create a condition: the condition is that a real
bank grants different people different visibility, which needs no invention.

## Idempotency

Safely re-runnable. `CREATE TABLE IF NOT EXISTS`, and the grants upsert on
their natural key. Verified afterwards by NAMING A VALUE rather than counting
rows -- a count cannot see a prefix being rewritten.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ccf.config import PG_SCHEMA_V2, pg_connect  # noqa: E402

S = PG_SCHEMA_V2

SCOPES: dict[str, list[str]] = {
    "PRIN-COV-001": ["US"],
    "PRIN-RES-002": ["US", "GB", "CA"],
    "PRIN-TRD-003": ["GB", "HK", "SG", "JP"],
    "PRIN-KYC-004": ["AT", "BE", "DE", "ES", "HU", "IT", "LU", "NL", "SE"],
}

DDL = f'''
CREATE TABLE IF NOT EXISTS "{S}".principal_jurisdiction (
    principal_id         TEXT NOT NULL
        REFERENCES "{S}".principal(principal_id),
    -- A country code, or an ISO 3166-2 subdivision. `US` admits `US-DE`;
    -- `US-DE` does NOT admit `US-MD`. Entitlement narrows, never widens.
    jurisdiction_prefix  TEXT NOT NULL,
    provenance           TEXT NOT NULL,
    PRIMARY KEY (principal_id, jurisdiction_prefix)
)
'''


def main() -> int:
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)

        cur.execute(f'SELECT principal_id FROM "{S}".principal')
        known = {r[0] for r in cur.fetchall()}
        unknown = set(SCOPES) - known
        if unknown:
            print(f"  principals not in {S}.principal: {sorted(unknown)}")
            return 2

        for pid, prefixes in SCOPES.items():
            for prefix in prefixes:
                cur.execute(
                    f'INSERT INTO "{S}".principal_jurisdiction '
                    "(principal_id, jurisdiction_prefix, provenance) "
                    "VALUES (%s, %s, %s) "
                    "ON CONFLICT (principal_id, jurisdiction_prefix) "
                    "DO UPDATE SET provenance = EXCLUDED.provenance",
                    (pid, prefix, "synthetic — internal"))
        conn.commit()

        # Named-value verification, not a count. A count cannot see `GB` being
        # rewritten to `GG`, and cannot see the EU analyst quietly acquiring
        # GB -- the one prefix whose absence is a deliberate statement.
        cur.execute(f'SELECT jurisdiction_prefix FROM "{S}".principal_jurisdiction '
                    "WHERE principal_id = 'PRIN-KYC-004' ORDER BY 1")
        eu = [r[0] for r in cur.fetchall()]
        assert eu == sorted(SCOPES["PRIN-KYC-004"]), eu
        assert "GB" not in eu, "GB is not in the EU; that absence is the point"

        cur.execute(f'SELECT count(*), count(DISTINCT principal_id) '
                    f'FROM "{S}".principal_jurisdiction')
        grants, principals = cur.fetchone()

    print(f"  {grants} grants across {principals} principals")
    print(f"  PRIN-KYC-004 scope verified by value: {', '.join(eu)}")
    print("  provenance: synthetic — internal (CLAUDE.md rule 1)")
    print("\n  Visibility is NOT stored. Run validators/entitlement.py, which "
          "recomputes\n  it from legal_entity.legal_jurisdiction on every run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
