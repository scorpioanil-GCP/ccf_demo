#!/usr/bin/env python3
"""Compare what the VAULT CLAIMS about each bound term against what the estate holds.

This is deliberately not "does the binding table match the estate." That framing
misses the error that produced it. On 2026-08-17 the vault published a currency
caveat saying the estate contradicted `owns` and `controls`; the sentence was
true when written and false a few hours later, because the remediation landed in
between. The term had not drifted. The *claim about it* had.

So the comparison is three-cornered:

    published_claims.json   what the vault currently tells consumers
    Fluree fibo-v2          what the estate actually asserts
    the corrected IRI       what the binding contract says is right

A caveat is a claim about mutable state frozen into an immutable document. It has
no expiry and nothing recomputes it, so it decays in BOTH directions:

    the drift outlives the warning  -> a consumer binds against stale data
    the warning outlives the drift  -> a consumer "fixes" data that is correct

The second is the more expensive failure, because the remedy it induces breaks
working code, and because nothing in the vault can detect it — the fact lives in
the estate. That asymmetry is the whole reason this runs here and not there.

Verdicts:

    AGREE          claim matches the estate
    CAVEAT_STALE   the vault warns of drift that no longer exists (or never did)
    CAVEAT_MISSING the estate is contradicted and the vault says otherwise
    CAVEAT_WRONG   the vault asserts data exists that does not
    CLAIM_MISSING  the estate holds a bound term the vault makes no claim about

Read-only.

    uv run validators/binding_drift.py
    uv run validators/binding_drift.py --json     # machine-readable, for CI
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf import fluree
from ccf.config import FLUREE_LEDGER_V2, REPO_ROOT

CLAIMS = REPO_ROOT / "sources" / "screening" / "published_claims.json"
CONFIRMED = REPO_ROOT / "sources" / "screening" / "fibo_wave8_confirmed.json"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

AGREE = "AGREE"
CAVEAT_STALE = "CAVEAT_STALE"
CAVEAT_MISSING = "CAVEAT_MISSING"
CAVEAT_WRONG = "CAVEAT_WRONG"
CLAIM_MISSING = "CLAIM_MISSING"

FAILING = (CAVEAT_STALE, CAVEAT_MISSING, CAVEAT_WRONG, CLAIM_MISSING)


def shape_of(kind: str) -> str:
    """'class' | 'property' | 'individual', from a recorded FIBO kind string.

    Three shapes, not two. A term can be asserted in the estate in three
    distinct positions, and asking the wrong one returns a confident zero:

        class        the object of rdf:type      ?s a <iri>
        property     the predicate               ?a <iri> ?b
        individual   the object of some triple   ?s ?p <iri>

    The third arrived with Wave 15. FIBO models enumerations as a classifier
    class plus `owl:NamedIndividual` values -- `PrimaryLienPosition` is never a
    type and never a predicate; it is a VALUE. Counted as a property it scores
    0, and a 0 here is indistinguishable from "not loaded", so the term would
    be silently skipped by the CLAIM_MISSING sweep below no matter how many
    assertions carried it. Kind strings may be compound
    ("LenderLienPosition+NamedIndividual"), so this matches on substrings.
    """
    if "NamedIndividual" in kind:
        return "individual"
    if "Property" in kind:
        return "property"
    return "class"


def count(iri: str | None, shape: str | bool) -> int:
    """Assertions currently in the estate for `iri`. -1 if the query failed.

    `shape` accepts the legacy bool (True == class) so the published-claims
    path, whose kinds are only "class"/"property", keeps working unchanged.
    """
    if not iri:
        return 0
    if shape is True:
        shape = "class"
    elif shape is False:
        shape = "property"
    if shape == "class":
        sparql = (f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
                  f"WHERE {{ ?s <{RDF_TYPE}> <{iri}> }}")
    elif shape == "individual":
        sparql = (f"SELECT (COUNT(*) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
                  f"WHERE {{ ?s ?p <{iri}> }}")
    else:
        sparql = (f"SELECT (COUNT(*) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
                  f"WHERE {{ ?a <{iri}> ?b }}")
    try:
        return int(fluree.query(sparql)["results"]["bindings"][0]["n"]["value"])
    except Exception:  # noqa: BLE001
        return -1


def judge(claim: str, correct_n: int, stale_n: int) -> tuple[str, str]:
    """Compare one published claim against the estate. Returns (verdict, why)."""
    if claim == "contradicted":
        if stale_n > 0:
            return AGREE, f"{stale_n} stale assertions, as claimed"
        if correct_n > 0:
            return CAVEAT_STALE, (
                f"remediation landed — {correct_n} assertions on the CORRECT IRI "
                f"and 0 stale. The caveat now tells consumers to distrust data "
                f"that is right; 'fixing' it would break working code"
            )
        return CAVEAT_STALE, "nothing asserted either way — there is no drift to warn about"

    if claim == "materialized":
        if correct_n > 0:
            return AGREE, f"{correct_n} assertions on the correct IRI, as claimed"
        if stale_n > 0:
            return CAVEAT_MISSING, (
                f"claimed materialized, but the estate holds {stale_n} assertions "
                f"on the STALE IRI — consumers need a drift warning here"
            )
        return CAVEAT_WRONG, "claimed materialized; the estate holds nothing"

    if claim == "not_materialized":
        if stale_n > 0:
            return CAVEAT_MISSING, (
                f"claimed not materialized, but {stale_n} stale assertions exist — "
                f"an empty result here means WRONG, not absent"
            )
        if correct_n > 0:
            return CAVEAT_STALE, (
                f"data landed since publication — {correct_n} assertions on the "
                f"correct IRI. Consumers are told to expect nothing"
            )
        return AGREE, "nothing asserted, as claimed"

    return CAVEAT_WRONG, f"unrecognised claim '{claim}'"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    doc = json.loads(CLAIMS.read_text())
    claims = doc["claims"]

    results = []
    for c in claims:
        is_class = c["kind"] == "class"
        correct_n = count(c.get("claimed_iri"), is_class)
        stale_n = count(c.get("stale_iri"), is_class)
        verdict, why = judge(c["claim"], correct_n, stale_n)
        results.append({
            "term": c["term"], "claim": c["claim"], "verdict": verdict,
            "correct_assertions": correct_n, "stale_assertions": stale_n,
            "why": why, "published_in": c.get("published_in", []),
        })

    # A bound term the estate holds but no claim covers is a silent gap: a
    # consumer gets no guidance at all, which reads as "nothing to know."
    claimed_iris = {c.get("claimed_iri") for c in claims}
    if CONFIRMED.exists():
        for row in json.loads(CONFIRMED.read_text())["confirmed"]:
            if row["iri"] in claimed_iris:
                continue
            n = count(row["iri"], shape_of(row.get("kind", "")))
            if n > 0:
                results.append({
                    "term": row["local_name"], "claim": "(none)",
                    "verdict": CLAIM_MISSING,
                    "correct_assertions": n, "stale_assertions": 0,
                    "why": f"estate holds {n} assertions; the vault makes no claim",
                    "published_in": [],
                })

    if args.json:
        print(json.dumps({
            "ledger": FLUREE_LEDGER_V2,
            "claims_as_of": doc.get("as_of"),
            "mirror_revision": doc.get("mirror_revision"),
            "results": results,
        }, indent=2))
        return 1 if any(r["verdict"] in FAILING for r in results) else 0

    print("BINDING DRIFT — published claims vs. the estate")
    print(f"  claims file: {CLAIMS.relative_to(REPO_ROOT)} "
          f"(as of {doc.get('as_of')}, mirror {doc.get('mirror_revision')})")
    print(f"  ledger:      {FLUREE_LEDGER_V2}\n")

    failures = [r for r in results if r["verdict"] in FAILING]
    for r in sorted(results, key=lambda x: (x["verdict"] == AGREE, x["term"])):
        mark = "ok  " if r["verdict"] == AGREE else "FAIL"
        print(f"  [{mark}] {r['term']:<28} claim={r['claim']:<17} {r['verdict']}")
        print(f"         correct={r['correct_assertions']}  stale={r['stale_assertions']}")
        if r["verdict"] != AGREE:
            print(f"         → {r['why']}")
            if r["published_in"]:
                print(f"         → update: {', '.join(r['published_in'])}")
        print()

    print(f"  {len(results) - len(failures)} agree · {len(failures)} disagree\n")
    if failures:
        print("  Every disagreement is a document to edit, not data to change.")
        print("  Check the direction before acting: a CAVEAT_STALE means the estate")
        print("  is RIGHT and the warning is wrong.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
