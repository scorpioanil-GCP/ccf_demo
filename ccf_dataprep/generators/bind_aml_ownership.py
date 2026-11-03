#!/usr/bin/env python3
"""Wave 17 Task 9 — bind AML parties to the inherited PSC-* / bo_chain island.

The design's central reuse decision. Rather than minting a second, parallel
beneficial-ownership population for `aml_party`, this task hitches a subset
of the 201-party population onto the ownership structures Wave 13b already
built and already proved safe: `psc_person` (210 rows, none of which touch a
real company) and the 50 `bo_chain` rows anchored on it.

## The boundary this task must never cross

There are two person populations in this database, with OPPOSITE safety
properties (CLAUDE.md rule 2, a legal constraint, not a style preference):

    PSC-####   -- touches no real company. 0 rows in person_role.
    numeric    -- officers OF real companies. 817 person_role rows join
                  legal_entity.

Candidate owners are selected with `WHERE person_key LIKE 'PSC-%'` at the SQL
level AND run through `ccf.aml.is_psc_key()` at the code level. The two
checks are deliberately redundant — one is easy to edit without noticing,
and this estate has a documented history of exactly that kind of drift.

## What gets bound, and to what

Only `aml_party` rows with `party_kind` in `{shell, individual_owned}` (100
of the 201) receive a `beneficial_owner_key`. `corporate` parties (101) stay
NULL — they are not modelled as owned by a single natural person here.

Every bound owner is a `person_key` already present in `bo_chain` (46
distinct persons across 50 chains) — reused, never minted fresh. 100
candidates over 50 existing chains means several parties legitimately share
one beneficial owner, which is not a defect: one controller sitting behind
several shell entities is the ordinary shape of the typology this product
exists to demonstrate, not an artifact of insufficient supply. No new
bo_chain row, no new PSC person, and no invented holding company are needed
to cover the 100 candidates, so none are minted. (Had the candidate count
exceeded the reachable supply, the fallback the brief allows is to build a
fresh chain from invented holding companies exactly as `bo_chain` already
does — never anchoring on a real `legal_entity` — but that branch is not
exercised here because it was never needed.)

## Determinism

`Random(SEED)` with a fixed integer constant, sampling only from lists read
back in a stable sort order (`party_id`, `chain_id` — both content keys, so
this is not the positional-identity defect: nothing here is keyed to a row's
place in an ORDER-BY-less scan or an unstable LIMIT/OFFSET). Re-running this
generator against an unchanged database reproduces the same JSON byte for
byte.

Output: sources/screening/wave17_ownership.json

    uv run generators/bind_aml_ownership.py
"""

from __future__ import annotations

import json
import sys
from random import Random

from ccf.aml import is_psc_key
from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect

S = PG_SCHEMA_V2
SCREEN = REPO_ROOT / "sources" / "screening"

#: Fixed constant, not derived from wall-clock time, so output is
#: reproducible across runs. Matches Wave 13b's convention of a date-shaped
#: seed (generate_bo_chains_wave13b.py: Random(20260822)).
SEED = 20260825

#: The only kinds this task binds. `corporate` parties are deliberately
#: left untouched -- see module docstring.
BOUND_KINDS = ("shell", "individual_owned")


def select_owner_candidates(cur) -> list[dict]:
    """Read the reusable bo_chain population.

    `WHERE person_key LIKE 'PSC-%'` (SQL) and `is_psc_key()` (code) are
    deliberately redundant -- see module docstring. A row failing the
    code-level check is dropped, never silently accepted.
    """
    cur.execute(
        f'''SELECT chain_id, entity_id, person_key, depth, effective_pct,
                   jurisdiction_path
            FROM "{S}".bo_chain
            WHERE person_key LIKE 'PSC-%'
            ORDER BY chain_id'''
    )
    rows = cur.fetchall()
    candidates = []
    for chain_id, entity_id, person_key, depth, effective_pct, jpath in rows:
        if not is_psc_key(person_key):
            continue  # redundant guard tripped -- drop, do not use
        candidates.append({
            "chain_id": chain_id,
            "entity_id": entity_id,
            "person_key": person_key,
            "depth": depth,
            "effective_pct": float(effective_pct),
            "jurisdiction_path": list(jpath),
        })
    return candidates


def select_bindable_parties(cur) -> list[dict]:
    """aml_party rows this task is allowed to touch: shell and
    individual_owned kinds only, sorted by party_id (a content key, not a
    row position)."""
    cur.execute(
        f'''SELECT party_id, party_kind FROM "{S}".aml_party
            WHERE party_kind = ANY(%s)
            ORDER BY party_id''',
        (list(BOUND_KINDS),),
    )
    return [{"party_id": r[0], "party_kind": r[1]} for r in cur.fetchall()]


def build_bindings(parties: list[dict], candidates: list[dict],
                    seed: int = SEED) -> list[dict]:
    """Deterministically assign each party an existing bo_chain's owner.

    `parties` and `candidates` must already be in a stable, content-derived
    sort order (party_id, chain_id) -- the caller's job, not this
    function's. `rng.choice` draws WITH replacement because 100 candidate
    parties exceed the 50 available chains; reuse (a shared owner) is the
    intended outcome, not a workaround.
    """
    rng = Random(seed)
    bindings = []
    for party in parties:
        chain = rng.choice(candidates)
        bindings.append({
            "party_id": party["party_id"],
            "party_kind": party["party_kind"],
            "beneficial_owner_key": chain["person_key"],
            "reused_chain_id": chain["chain_id"],
            "reused_entity_id": chain["entity_id"],
            "reused_chain_depth": chain["depth"],
            "reused_chain_effective_pct": chain["effective_pct"],
            "reused_chain_jurisdiction_path": chain["jurisdiction_path"],
            "provenance": "synthetic — engineered",
        })
    return bindings


def main() -> int:
    with pg_connect() as conn, conn.cursor() as cur:
        candidates = select_owner_candidates(cur)
        parties = select_bindable_parties(cur)

    print("Wave 17 Task 9 — bind AML parties to the PSC-* / bo_chain island\n")
    print(f"  bo_chain owner candidates   {len(candidates)}   "
          f"({len({c['person_key'] for c in candidates})} distinct persons)")
    print(f"  bindable parties            {len(parties)}   "
          f"(kinds: {', '.join(BOUND_KINDS)})")

    if not candidates:
        print("  FAIL: no PSC-anchored bo_chain rows available to reuse")
        return 1
    if not parties:
        print("  FAIL: no shell/individual_owned parties found in aml_party")
        return 1

    bad_form = [c["person_key"] for c in candidates if not is_psc_key(c["person_key"])]
    if bad_form:
        print(f"  FAIL: non-PSC owner key(s) survived filtering: {bad_form[:5]}")
        return 1

    bindings = build_bindings(parties, candidates)

    used_persons = {b["beneficial_owner_key"] for b in bindings}
    used_chains = {b["reused_chain_id"] for b in bindings}
    print(f"\n  bindings written            {len(bindings)}")
    print(f"  distinct owners reused      {len(used_persons)}")
    print(f"  distinct chains reused      {len(used_chains)}")
    print(f"  new chains minted           0 (reuse fully covered demand)")

    out = SCREEN / "wave17_ownership.json"
    out.write_text(
        json.dumps(
            {
                "generated_for": "Wave 17 Task 9 — bind aml_party.beneficial_"
                                  "owner_key to the existing PSC-* / bo_chain "
                                  "island. PSC-* only, never a numeric person "
                                  "key (CLAUDE.md rule 2).",
                "seed": SEED,
                "bound_kinds": list(BOUND_KINDS),
                "provenance": "synthetic — engineered",
                "binding_count": len(bindings),
                "distinct_owners_reused": len(used_persons),
                "distinct_chains_reused": len(used_chains),
                "bindings": bindings,
            },
            indent=1,
            ensure_ascii=False,
        )
        + "\n"
    )
    print(f"\n  written: {out.relative_to(REPO_ROOT)} "
          f"({out.stat().st_size / 1e3:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
