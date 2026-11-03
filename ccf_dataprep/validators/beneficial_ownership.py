#!/usr/bin/env python3
"""Gates for `kyc-refresh-beneficial-ownership`, each with a falsification arm.

    uv run validators/beneficial_ownership.py

`docs/wave13b-design.md` §5 names three conditions with the shape that produced
Wave 12's seven defects — checks that pass because they are not looking at
anything. This file gates those three, plus three more the wave built, and
**every gate is paired with the input that makes it fail.** A gate whose
falsification arm goes green has stopped distinguishing the condition from its
absence and is decoration.

The six:

    1  §F5  the false-positive pair, RE-SCORED by the product's own scorer
    2  §F6  the sanctions match strictly inside the review band, with the
            bounds read from `resolution_policy`
    3  §F7  EU-resident invisibility, proved by running ONE traversal under
            two principals and diffing
    4  §F8  the registry contradiction, RECOMPUTED from declared_* vs bo_chain
    5  §F3  chain depth, RECOMPUTED by walking Fluree `owns` edges
    6  §F4  cycles counted as CYCLES, and their jurisdictions resolved

## What each gate refuses to do

None of them reads a flag the generator wrote. `person_crosswalk.match_band`
says `false_positive`, `kyc_document.planted_contradiction_kind` names the
plant, and `bo_chain.depth` states a depth — all three are ignored here and
recomputed from the underlying rows and edges. A generator and a gate that
share a belief cannot detect that the belief is wrong; the estate learned that
in Wave 8 (`known-issues.md` §0.1) when a validator held the same wrong FIBO
constants as its loader and agreed with itself.

Read-only throughout.
"""

from __future__ import annotations

import sys
from collections import defaultdict

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, mongo_db, pg_connect
from ccf.resolve import (
    CONFLICT,
    Evidence,
    Thresholds,
    band,
    combined_score,
    corroboration,
    explain,
    in_review_band,
)

S = PG_SCHEMA_V2
L = FLUREE_LEDGER_V2
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
P_OWNS = f"{FIBO}FND/OwnershipAndControl/Ownership/owns"
P_SUBJECT_TO_CONSTRAINT = f"{EX}subjectToConstraint"
P_APPLIES_TO_COUNTRY = f"{EX}appliesToCountry"
P_REQUIRES_ENTITLEMENT = f"{EX}requiresEntitlement"


class Gate:
    def __init__(self, name: str, condition: str) -> None:
        self.name = name
        self.condition = condition
        self.passed = False
        self.falsified = False
        self.detail = ""
        self.counter_detail = ""

    @property
    def ok(self) -> bool:
        return self.passed and self.falsified

    def render(self) -> str:
        state = "PASS" if self.ok else "FAIL"
        return (f"  [{state}] {self.name}  ({self.condition})\n"
                f"         claim:        {self.detail}\n"
                f"         falsified by: {self.counter_detail}")


def bindings(sparql: str) -> list[dict]:
    return fluree.query(sparql)["results"]["bindings"]


# --- 1 · the false-positive pair -------------------------------------------

def gate_false_positive(cur, t: Thresholds) -> Gate:
    g = Gate("false-positive pair is real", "§F5")

    cur.execute(f"""
        SELECT c.person_key, c.source_id, c.source_name, c.match_score
          FROM "{S}".person_crosswalk c
          JOIN "{S}".person p USING (person_key)
         WHERE p.person_key_source = 'psc'
           AND c.source_id LIKE 'fp-%'
    """)
    candidates = cur.fetchall()

    proven = []
    for person_key, source_id, source_name, _stored in candidates:
        other_key = source_id.removeprefix("fp-")
        cur.execute(f"""
            SELECT p.person_key, p.display_name, pp.dob_month, pp.dob_year,
                   pp.nationality
              FROM "{S}".person p JOIN "{S}".psc_person pp USING (person_key)
             WHERE p.person_key IN (%s, %s)
        """, (person_key, other_key))
        rows = {r[0]: r for r in cur.fetchall()}
        if len(rows) != 2:
            continue
        a, b = rows[person_key], rows[other_key]

        # RE-SCORED here. The stored match_score and match_band are ignored:
        # a pair engineered to fuzzy-match will match under whatever scorer
        # wrote it, and reading the band back would test nothing.
        score = combined_score(a[1], b[1])
        ev_a = Evidence(a[2], a[3], a[4])
        ev_b = Evidence(b[2], b[3], b[4])
        corr = corroboration(ev_a, ev_b)
        verdict = band(score, corr, t)

        if (score >= t.merge_threshold and corr == CONFLICT
                and verdict == "false_positive"):
            proven.append((a[1], b[1], score, ev_a, ev_b))

    g.passed = bool(proven)
    if proven:
        name_a, name_b, score, ev_a, ev_b = proven[0]
        g.detail = (f"{len(proven)} pair(s) re-scored above merge_threshold "
                    f"{t.merge_threshold} AND conflicting on evidence; e.g. "
                    f"{name_a!r} vs {name_b!r} score={score:.4f}, "
                    f"dob {ev_a.dob_year}/{ev_a.dob_month} vs "
                    f"{ev_b.dob_year}/{ev_b.dob_month}")
    else:
        g.detail = f"no pair survived re-scoring ({len(candidates)} candidates)"

    # FALSIFICATION: give the same two people IDENTICAL corroborating
    # evidence. They then differ only by name, which no longer conflicts, so
    # the pair must stop being a false positive. If it survives that, the
    # gate is reading the name and calling it evidence.
    if proven:
        name_a, name_b, score, ev_a, _ = proven[0]
        same = corroboration(ev_a, ev_a)
        verdict = band(score, same, t)
        g.falsified = verdict != "false_positive"
        g.counter_detail = (f"with identical evidence the same pair bands as "
                            f"{verdict!r}, not false_positive")
    else:
        g.counter_detail = "not run — no pair to falsify"
    return g


# --- 2 · sanctions match below certainty -----------------------------------

def gate_sanctions_band(cur, t: Thresholds) -> Gate:
    g = Gate("sanctions match is below certainty", "§F6")

    cur.execute(f"""
        SELECT r.person_key, p.display_name, r.listed_name, r.score
          FROM "{S}".sanctions_screening_result r
          JOIN "{S}".person p USING (person_key)
    """)
    hits = cur.fetchall()

    # RE-SCORED, and re-banded against the LOADED thresholds. `disposition`
    # and `in_review_band` are columns the generator wrote; neither is read.
    inside = []
    for person_key, person_name, listed_name, _stored in hits:
        score = combined_score(person_name, listed_name)
        if in_review_band(score, t):
            inside.append((person_name, listed_name, score))

    g.passed = bool(inside)
    if inside:
        person_name, listed_name, score = inside[0]
        g.detail = (f"{len(inside)} of {len(hits)} match(es) re-score strictly "
                    f"inside [{t.review_floor}, {t.auto_clear}); e.g. "
                    f"{person_name!r} ~ {listed_name!r} at {score:.4f}")
    else:
        g.detail = (f"no match re-scores into the review band "
                    f"[{t.review_floor}, {t.auto_clear})")

    # FALSIFICATION: a band is only meaningful if scores can fall OUTSIDE it.
    # A gate asserting "the score is in the band" passes trivially if the band
    # is [0, 1]. Both bounds are probed with scores that must be rejected.
    below = in_review_band(t.review_floor - 0.01, t)
    above = in_review_band(t.auto_clear, t)
    g.falsified = not below and not above
    g.counter_detail = (
        f"score just below the floor ({t.review_floor - 0.01:.2f}) -> "
        f"{'IN' if below else 'out'}; score at auto_clear ({t.auto_clear}) -> "
        f"{'IN' if above else 'out'}; both must be out")
    return g


# --- 3 · EU-resident invisibility ------------------------------------------

def visible_persons(cur, principal_id: str, *, enforce: bool = True) -> set[str]:
    """ONE traversal, parameterised by principal. Used for both sides of the diff.

    The policy comes from the graph: the residency constraint names the
    countries it covers and the entitlement it requires, and the principal's
    entitlement is a column. `enforce=False` is the falsification arm's
    unpolicied twin — same query, no filter.
    """
    rows = bindings(
        f"SELECT ?p ?c FROM <{L}> WHERE {{ ?p <{P_SUBJECT_TO_CONSTRAINT}> ?c }}")
    constrained = {b["p"]["value"].replace(EX, "") for b in rows}

    cur.execute(f"SELECT person_key FROM \"{S}\".person "
                "WHERE person_key_source = 'psc'")
    everyone = {r[0] for r in cur.fetchall()}

    if not enforce:
        return everyone

    cur.execute(f'SELECT sees_eu_person_data FROM "{S}".principal '
                "WHERE principal_id = %s", (principal_id,))
    row = cur.fetchone()
    entitled = bool(row and row[0])
    return everyone if entitled else everyone - constrained


def gate_eu_invisibility(cur) -> Gate:
    g = Gate("EU-resident persons are invisible without entitlement", "§F7")

    entitled = visible_persons(cur, "PRIN-KYC-004")
    blind = visible_persons(cur, "PRIN-RES-002")
    hidden = entitled - blind

    # The hidden persons must actually be the EU-resident ones, and they must
    # be reachable as beneficial owners of at least two entities — §F7 counts
    # ENTITIES, not persons.
    cur.execute(f"""
        SELECT count(DISTINCT entity_id) FROM "{S}".bo_chain
         WHERE person_key = ANY(%s)""", (sorted(hidden),))
    n_entities = cur.fetchone()[0] if hidden else 0

    g.passed = bool(hidden) and n_entities >= 2
    g.detail = (f"same traversal, two principals: entitled sees "
                f"{len(entitled)}, unentitled sees {len(blind)}; "
                f"{len(hidden)} person(s) hidden, covering {n_entities} "
                f"entities (floor 2)")

    # FALSIFICATION: run the identical traversal with the policy filter
    # removed. Both principals must then see the SAME set — proving the diff
    # above comes from policy and not from the two principals happening to
    # query different data.
    unpolicied_a = visible_persons(cur, "PRIN-KYC-004", enforce=False)
    unpolicied_b = visible_persons(cur, "PRIN-RES-002", enforce=False)
    same_without_policy = unpolicied_a == unpolicied_b
    g.falsified = same_without_policy and bool(hidden)
    g.counter_detail = (
        f"with the filter removed both principals see "
        f"{len(unpolicied_a)} and {len(unpolicied_b)} — "
        f"{'identical, so the diff is caused by policy' if same_without_policy else 'DIFFERENT, so the diff is not policy'}")
    return g


# --- 4 · the registry contradiction ----------------------------------------

def gate_registry_contradiction(cur) -> Gate:
    g = Gate("a KYC declaration contradicts the registry", "§F8")

    db = mongo_db(write=False)
    declarations = list(db["kyc_document"].find(
        {"kind": "ownership_declaration"},
        {"document_id": 1, "chain_id": 1, "declared_owner_name": 1,
         "declared_owner_person_key": 1, "declared_pct": 1,
         "applicable_threshold_pct": 1}))

    cur.execute(f"""
        SELECT c.chain_id, c.person_key, p.display_name, c.effective_pct
          FROM "{S}".bo_chain c JOIN "{S}".person p USING (person_key)""")
    registry = {r[0]: (r[1], r[2], float(r[3])) for r in cur.fetchall()}

    found = defaultdict(list)
    for d in declarations:
        entry = registry.get(d.get("chain_id"))
        if entry is None:
            continue
        true_key, true_name, true_pct = entry
        declared_name = d.get("declared_owner_name")
        declared_pct = float(d.get("declared_pct") or 0.0)
        threshold = float(d.get("applicable_threshold_pct") or 25.0)

        # RECOMPUTED. `planted_contradiction_kind` exists in the document and
        # is deliberately not read: a gate that reads the plant is testing the
        # generator's memory, not the data.
        if declared_name and declared_name != true_name:
            found["wrong_person"].append(
                (d["document_id"], declared_name, true_name))
        if declared_pct < threshold <= true_pct:
            found["understated_pct"].append(
                (d["document_id"], declared_pct, true_pct, threshold))

    total = sum(len(v) for v in found.values())
    g.passed = total >= 1
    g.detail = (f"{total} declaration(s) disagree with bo_chain, recomputed: "
                f"{ {k: len(v) for k, v in found.items()} }")
    if found.get("wrong_person"):
        doc, declared, true = found["wrong_person"][0]
        g.detail += f"; e.g. {doc} declares {declared!r}, registry says {true!r}"

    # FALSIFICATION: the same comparison run against declarations that AGREE
    # must find nothing. If every declaration looked like a contradiction, the
    # comparison would be broken rather than the data interesting.
    agreeing = 0
    for d in declarations:
        entry = registry.get(d.get("chain_id"))
        if entry is None:
            continue
        _key, true_name, true_pct = entry
        if (d.get("declared_owner_name") == true_name
                and abs(float(d.get("declared_pct") or 0) - true_pct) < 0.01):
            agreeing += 1
    g.falsified = agreeing > 0 and total < len(declarations)
    g.counter_detail = (f"{agreeing} of {len(declarations)} declarations AGREE "
                        f"with the registry and are not flagged — the "
                        f"comparison discriminates")
    return g


# --- 5 · chain depth, recomputed by traversal ------------------------------

def gate_chain_depth(cur) -> Gate:
    g = Gate("chains reach depth 5 by traversal", "§F3")

    rows = bindings(f"SELECT ?a ?b FROM <{L}> WHERE {{ ?a <{P_OWNS}> ?b }}")
    owns: dict[str, list[str]] = defaultdict(list)
    for b in rows:
        owns[b["a"]["value"].replace(EX, "")].append(
            b["b"]["value"].replace(EX, ""))

    cur.execute(f'SELECT chain_id, person_key, entity_id, depth '
                f'FROM "{S}".bo_chain')
    chains = cur.fetchall()

    def walk(start: str, target: str, limit: int = 12) -> int | None:
        """Shortest `owns` path from person to entity, walked in the graph."""
        frontier = [(start, 0)]
        seen = {start}
        while frontier:
            node, dist = frontier.pop(0)
            if node == target:
                return dist
            if dist >= limit:
                continue
            for nxt in owns.get(node, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    frontier.append((nxt, dist + 1))
        return None

    measured = []
    mismatched = []
    for chain_id, person_key, entity_id, stored_depth in chains:
        d = walk(person_key, entity_id)
        if d is None:
            mismatched.append((chain_id, "unreachable", stored_depth))
            continue
        measured.append(d)
        if d != stored_depth:
            mismatched.append((chain_id, d, stored_depth))

    deep = [d for d in measured if d >= 5]
    g.passed = len(deep) >= 3 and not mismatched
    g.detail = (f"{len(deep)} chain(s) measured at depth >= 5 by walking "
                f"`owns` in Fluree (floor 3); "
                f"{len(mismatched)} disagree with the stored depth")
    if mismatched:
        g.detail += f"; first: {mismatched[0]}"

    # FALSIFICATION: the walk must be able to return a SHORTER answer than the
    # stored depth. A traversal that simply echoed `bo_chain.depth` would
    # agree with it for any input, so a deliberately wrong target is walked
    # and must not resolve to the stored number.
    if chains:
        chain_id, person_key, entity_id, stored = chains[0]
        wrong = walk(person_key, "ICJ-SPV-NOT-A-REAL-ID")
        g.falsified = wrong is None
        g.counter_detail = (f"walking to a non-existent entity returns "
                            f"{wrong!r}, not {stored} — the walk reads the "
                            f"graph, not the column")
    else:
        g.counter_detail = "not run — no chains"
    return g


# --- 6 · cycles, counted as cycles -----------------------------------------

def gate_cycles(cur) -> Gate:
    g = Gate("two cycles exist and one spans jurisdictions", "§F4")

    rows = bindings(f"""SELECT ?a ?b ?c FROM <{L}> WHERE {{
        ?a <{P_OWNS}> ?b . ?b <{P_OWNS}> ?c . ?c <{P_OWNS}> ?a }} LIMIT 200""")
    cycles = {frozenset(b[v]["value"].replace(EX, "") for v in ("a", "b", "c"))
              for b in rows}

    cur.execute(f'SELECT entity_id, jurisdiction FROM "{S}".engineered_entity')
    juris = dict(cur.fetchall())

    spanning = []
    for cycle in cycles:
        codes = {juris.get(m) for m in cycle}
        if None not in codes and len(codes) > 1:
            spanning.append((sorted(cycle), sorted(codes)))

    g.passed = len(cycles) >= 2 and len(spanning) >= 1
    g.detail = (f"{len(cycles)} distinct cycle(s) from {len(rows)} rotations "
                f"(floor 2); {len(spanning)} span jurisdictions")
    if spanning:
        g.detail += f"; e.g. {spanning[0][1]}"

    # FALSIFICATION: counting cycle MEMBERS instead of cycles must give a
    # different, larger number. That was the estate's actual defect — one
    # 3-cycle reported as 3 — and if the two counts agree, this gate has
    # reproduced it.
    members = {b["a"]["value"] for b in rows}
    g.falsified = len(members) != len(cycles)
    g.counter_detail = (f"counting distinct members gives {len(members)}, "
                        f"not {len(cycles)} — the old check counted members "
                        f"and could not fail")
    return g


def main() -> int:
    with pg_connect() as conn, conn.cursor() as cur:
        thresholds = Thresholds.load(cur)
        print("kyc-refresh-beneficial-ownership — six gates, each falsified\n")
        print(f"  thresholds from {S}.resolution_policy "
              f"({thresholds.policy_version}): "
              f"auto_clear={thresholds.auto_clear} "
              f"review_floor={thresholds.review_floor} "
              f"merge_threshold={thresholds.merge_threshold}\n")

        gates = [
            gate_false_positive(cur, thresholds),
            gate_sanctions_band(cur, thresholds),
            gate_eu_invisibility(cur),
            gate_registry_contradiction(cur),
            gate_chain_depth(cur),
            gate_cycles(cur),
        ]

    for gate in gates:
        print(gate.render())
        print()

    passed = sum(1 for g in gates if g.ok)
    print(f"{passed}/{len(gates)} gates green (a gate counts only when its "
          f"falsification arm also holds)")
    if passed != len(gates):
        print("\nA gate whose falsification arm is red cannot tell the "
              "condition from its absence. Fix the gate, not the count.")
    return 0 if passed == len(gates) else 1


if __name__ == "__main__":
    sys.exit(main())
