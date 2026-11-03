#!/usr/bin/env python3
"""Wave 20 gap 2 -- no-LEI internal clients, and the blindness that hid them.

    uv run validators/internal_client.py

`counterparty-reference-snapshot` §C names *"Internal client identity for
no-LEI entities"*. §D says why: an LEI-only anchor silently excludes the
privately-held middle-market borrowers who make up a large share of the
Commercial Banking book, and every downstream product inherits the exclusion.

## The gate this module exists to be, rather than the one that failed

The predecessor §C row was marked COVERED against `conditions.py`'s crosswalk
floors, all of which are keyed on LEI:

    SELECT COUNT(*) FROM crosswalk c JOIN legal_entity e USING (lei)

An inner join on the property this population LACKS cannot report its absence.
The floor read a healthy 50 for the estate's whole life while the population
it was standing in for was 0 -- a gate selecting by the property it polices.

`lei_keyed_join_count` is kept here deliberately, not to measure anything the
product needs, but so the blindness is ASSERTED rather than remembered: the
gate proves on every run that the old floor still cannot see these clients.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

#: §D: LEI-registered entities carry a 24-hour freshness SLA.
LEI_TTL_HOURS = 24
#: Ours, not the spec's: v0.3 states no volume for this row.
POPULATION_FLOOR = 20


def resolves(row) -> bool:
    """Does this client actually resolve to an identity?

    Name AND jurisdiction, both non-blank. A row that exists and carries
    nothing is what "closing" this gap would look like if it were closed by
    inserting empty identifiers, and it would satisfy any count.
    """
    return bool((row.get("legal_name") or "").strip()
                and (row.get("legal_jurisdiction") or "").strip())


def reports_lower_ceiling(ceiling_days: int, lei_ttl_hours: int = LEI_TTL_HOURS) -> bool:
    """Is this client's freshness ceiling LOWER than an LEI-registered one's?

    "Lower ceiling" means *staler is permitted*, so the no-LEI duration must be
    the LARGER one -- §D puts LEI-registered at 24 hours and private no-LEI
    clients on a KYC cadence of months. A no-LEI client claiming an hourly
    refresh has been handed the public entity's SLA, which is precisely the
    misreporting §G's acceptance criterion is written to catch.
    """
    return ceiling_days * 24 > lei_ttl_hours


def lei_keyed_join_count(crosswalk, entities) -> int:
    """What an inner join on `lei` sees. Kept to prove what it CANNOT see."""
    leis = {e["lei"] for e in entities if e.get("lei")}
    return sum(1 for c in crosswalk if c.get("lei") and c["lei"] in leis)


def no_lei_clients(crosswalk) -> int:
    return sum(1 for c in crosswalk if not c.get("lei"))


# --------------------------------------------------------------------------
# live
# --------------------------------------------------------------------------

def _load():
    from ccf.config import PG_SCHEMA_V2, pg_connect
    S = PG_SCHEMA_V2
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT internal_client_id, legal_name, legal_jurisdiction, '
                    f'freshness_ceiling_days FROM "{S}".internal_client')
        clients = [{"internal_client_id": a, "legal_name": b,
                    "legal_jurisdiction": c, "freshness_ceiling_days": d}
                   for a, b, c, d in cur.fetchall()]
        cur.execute(f'SELECT internal_client_id, lei FROM "{S}".crosswalk')
        crosswalk = [{"internal_client_id": a, "lei": b} for a, b in cur.fetchall()]
        cur.execute(f'SELECT lei FROM "{S}".legal_entity')
        entities = [{"lei": r[0]} for r in cur.fetchall()]
    return clients, crosswalk, entities


def main() -> int:
    clients, crosswalk, entities = _load()
    ok = True
    print("NO-LEI INTERNAL CLIENTS — recomputed from the stores\n")

    n = len(clients)
    resolving = [c for c in clients if resolves(c)]
    stale_ok = [c for c in clients
                if reports_lower_ceiling(c["freshness_ceiling_days"] or 0)]
    nolei = no_lei_clients(crosswalk)
    blind = lei_keyed_join_count(
        [c for c in crosswalk if not c.get("lei")], entities)

    print(f"  {n} internal clients")
    print(f"  {len(resolving)} resolve to a name AND a jurisdiction")
    print(f"  {nolei} crosswalk rows carry lei IS NULL")
    print(f"  {len(stale_ok)} report a ceiling lower than the "
          f"{LEI_TTL_HOURS}h LEI-registered SLA\n")

    for label, got, want in (
            ("population", n, POPULATION_FLOOR),
            ("all resolve", len(resolving), n),
            ("all report the lower ceiling", len(stale_ok), n),
            ("crosswalk rows with no LEI", nolei, POPULATION_FLOOR)):
        if got >= want and want > 0:
            print(f"  [PASS] {label}: {got} / {want}")
        else:
            ok = False
            print(f"  [FAIL] {label}: {got} / {want}")

    # The blindness, asserted rather than remembered.
    if blind == 0 and nolei > 0:
        print(f"  [PASS] the LEI-keyed join sees 0 of the {nolei} no-LEI "
              f"clients — the old floor is still blind, by construction")
    else:
        ok = False
        print(f"  [FAIL] LEI-keyed join saw {blind} no-LEI clients, which "
              f"should be impossible")

    print("\n  §D: an LEI-only anchor silently excludes these borrowers, and "
          "every\n  downstream product inherits the exclusion.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
