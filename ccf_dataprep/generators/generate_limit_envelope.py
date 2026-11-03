#!/usr/bin/env python3
"""Wave 19 Task 9 — the limit envelope: real regime versions, one invented appetite.

Two populations, two provenance classes, one artifact.

## Part 1 — regime versions are REAL

`docs/spec-digest.md` lists "regime version history" among the engineered
elements. It does not have to be, and this generator does not invent one.
SI 2021/1078 (The Capital Requirements Regulation (Amendment) Regulations
2021) moved UK large-exposure regulation out of assimilated CRR and into the
PRA Rulebook's own Large Exposures Part, effective **2022-01-01** — CRR
Articles 392-403 stopped applying the day before. That boundary is a genuine
regulatory handover, not a manufactured one, and it alone satisfies §F's
"≥ 2 regime versions with distinct effective dates" (three, counting
Regulation O). Every `RegimeVersion` this generator writes is `public` and
every one of them **cites a live MongoDB passage**, resolved by regime +
provision label rather than hard-coded, exactly the discipline
`generate_insider_cases.py::verify_citations()` already established for this
wave — a citation is a claim, and claims get checked against the corpus that
is supposed to back them, every run, not copy-pasted once and trusted.

## The PRA citation — corrected in fix round 1

**First cut of this generator cited LE 2.3 as the source of the PRA
regime's 25% limit. That was wrong, and a coordinator review caught it.**
Measured across the whole PRA corpus: zero passages contain "must not
incur" or "shall not incur" — the PRA Large Exposures Part states **no
prohibition anywhere in what Task 2 fetched**. LE 2.3's "25%" is a
core-UK-group *notification* duty ("... likely to exceed, or have exceeded,
25% of the Tier 1 capital...") — a reporting trigger that happens to share
the number, not the provision that establishes it. Citing it as the limit's
source asserted something the passage does not say.

**The true mechanism, corrected:** SI 2021/1078 omitted CRR Articles
392-403 from assimilated UK law on 2022-01-01, but the PRA Large Exposures
Part that replaced them does **not restate the 25% limit** — it points back
at it. **LE 2.4** reads "A firm must exclude from **the limit in Article
395(1) of the CRR** resolution exposures to..." — an instrument that
applies and modifies a limit defined elsewhere, not the limit's source. So
the PRA `RegimeVersion` now cites **two** provisions with two different
jobs, made explicit rather than left to be inferred from the citation
order:

- **CRR Article 395(1)** (the same passage the CRR `RegimeVersion` cites) —
  the provision that actually **states** the 25% prohibition. The PRA
  regime's limit is still, textually, this provision's limit.
- **LE 2.4** — the PRA instrument that **applies and modifies** that limit
  for a UK firm post-boundary, and the corpus's own evidence that the
  cross-reference survives 2022-01-01 rather than being severed by it.

LE 2.3 is dropped entirely rather than re-labelled under a different
predicate: nothing in this wave's own conditions needs a "notification
threshold" fact recorded, and inventing a second predicate to keep a
citation this task does not otherwise need would be exactly the padding
CLAUDE.md warns against. A narrower, more direct PRA restatement of "25%"
may exist in the real Rulebook outside what Task 2 fetched; this generator
cites what is actually in the loaded corpus, not what might exist
elsewhere.

## Regulation O's effective-from date

Reg O's $500,000 cap has existed for decades; the eCFR snapshot Task 2/4
actually fetched is dated **2026-01-01** (`sources/regimes/manifest.json`'s
`full/2026-01-01/title-12.xml` fetch, and the passage's own stored
`effective_date` field — confirmed live below, not assumed). Using anything
earlier would assert a date this estate never actually retrieved text for.
`effective_from` is therefore the eCFR "current as of" date, not the
statute's original enactment date — a real, verifiable date, just not the
oldest one that could be claimed.

**Minor 4, fix round.** `effectiveFrom` means two different things across
the three RegimeVersion nodes: a genuine commencement date for CRR and PRA,
and a retrieval-date snapshot bound for Reg O — invisible to anything
reading the predicate alone, and a real hazard for an `as_of` replay before
2026 (the product this data serves exists specifically to do that replay).
Rather than inventing a commencement date this estate never verified, the
Reg O node is marked explicitly: `resolved_regime["effective_from_is_
retrieval_snapshot"] = True` here, carried through
`loaders/load_policy_fluree.py` as one additional literal triple,
`ex:effectiveFromIsSnapshot "true"`, asserted only on that node.
`effectiveFrom` itself is untouched (still the real eCFR date, still usable
as a lower bound), but a consumer doing `as_of` replay now has a way to
tell "this is when the cap took effect" from "this is only when we last
confirmed the text" without guessing.

## `effectiveTo` — absent, not a sentinel

A regime version still in force gets **no `ex:effectiveTo` triple at all** —
not a `9999-12-31` sentinel. A sentinel sorts correctly in a range query but
reads as a claim ("this regime ends on that date"), which is false for PRA
and Reg O. This estate's own bitemporal predicates already tolerate an
absent end (`ex:validTo`/`ex:assertedTo` on superseded facts are asserted
only when supersession actually happened); this follows the same
convention rather than inventing a new one. The cost is explicit: any
consumer asking "is this regime still in force as of some date" must treat
a missing `effectiveTo` as open-ended, not query it as a bound and get a
false "expired" reading from an unbound variable. Documented once here
rather than left for a future task to rediscover.

## Part 2 — the internal appetite, engineered, value re-derived live

§C classes the internal limit envelope `synthetic — internal`. Its level
must do two jobs at once:

1. sit **below** the largest real control-basis group (Bausch Health,
   ~5.41% of tier 1) so a real group breaches house policy while remaining
   compliant under both CRR and PRA's 25%;
2. sit inside Task 7's `(TransDigm-alone%, TransDigm+Vertiv-merged%]` band
   so the engineered `economicallyDependentOn` edge is *consequential* —
   changes which limit binds — not merely present.

**5.0% is used below only after this generator re-derives both boundary
numbers live** (`derive_group_exposures()`), rather than trusting Task 7's
report figures. The two independent computations agree to within the
tier 1 rounding Task 7's report used ($295.8bn headline vs the exact
$295,758,000,000 in `ccf_v2.bank_capital`) — see `main()`'s printed
reconciliation. If a live re-derivation ever disagreed beyond that
rounding, this generator refuses to write a value (see `main()`), because
adjusting the number to fit is exactly the failure this wave's brief warns
against.

Output: sources/screening/wave19_limit_envelope.json

    uv run generators/generate_limit_envelope.py
    uv run generators/generate_limit_envelope.py --dry-run   # skip writing the artifact
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2 as L, PG_SCHEMA_V2, REPO_ROOT, mongo_db, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave19_limit_envelope.json"

S = PG_SCHEMA_V2

REG_PROVENANCE = "public"
INTERNAL_PROVENANCE = "synthetic — internal"

#: The internal appetite, expressed as a percentage of tier 1 capital.
#: Re-derived and bounds-checked live in main() before being trusted —
#: this constant is a proposal, not an authority.
INTERNAL_APPETITE_PCT = 5.0

#: House-policy setting date. Not tied to any regulatory event — the
#: internal appetite is `synthetic — internal` and this is simply when the
#: engineered artifact asserts the policy took effect.
INTERNAL_APPETITE_EFFECTIVE_FROM = "2026-01-01"


# --------------------------------------------------------------------------
# Part 1 — regime versions, resolved against the live Mongo corpus
# --------------------------------------------------------------------------

#: (regime_version_key, label, regime, effective_from, effective_to,
#:  limit_pct_of_capital, limit_absolute_usd, citations)
#: citations is a list of (citation_regime, provision_label, document_id,
#: must_contain, role) -- citation_regime lets a RegimeVersion cite a
#: passage filed under a DIFFERENT regime than its own (the PRA version
#: below cites a CRR passage, because that is genuinely where the 25%
#: prohibition is stated -- see the module docstring's fix-round-1 note).
#: must_contain is text that has to appear in the resolved passage, the
#: same "a citation is a claim, verify it" discipline
#: generate_insider_cases.py uses for 215.4(b)(2) and 215.2(n)(1). role is
#: a short label for what the citation establishes, printed at load time so
#: the provision-to-claim mapping is visible rather than merely asserted.
REGIME_VERSIONS = [
    {
        "key": "crr-2014-2021",
        "label": "CRR (assimilated UK law) — large exposures",
        "regime": "crr",
        "effective_from": "2014-01-01",
        "effective_to": "2021-12-31",
        "limit_pct_of_capital": 25.0,
        "limit_absolute_usd": None,
        "citations": [
            # NBSP (U+00A0), not a plain space, between "25" and "%" in the
            # fetched legislation.gov.uk text -- confirmed live, not guessed.
            ("crr", "Article 395(1)", "crr-art-395-2021-12-31", "25 %",
             "states the 25% limit"),
        ],
    },
    {
        "key": "pra-2022",
        "label": "PRA Large Exposures Part",
        "regime": "pra",
        "effective_from": "2022-01-01",
        "effective_to": None,  # still in force -- see module docstring
        "limit_pct_of_capital": 25.0,
        "limit_absolute_usd": None,
        "citations": [
            # Fix round 1: LE 2.3 dropped -- its "25%" is a notification
            # duty, not the prohibition, and citing it as the limit's
            # source asserted something the passage does not say. The PRA
            # Part does not restate Article 395(1); it cross-references it.
            ("crr", "Article 395(1)", "crr-art-395-2021-12-31", "25 %",
             "states the 25% limit (same provision the CRR version cites)"),
            ("pra", "LE 2.4", "pra-large-exposures-01-01-2022",
             "Article 395(1) of the CRR",
             "the PRA instrument that applies/modifies that limit for a UK firm"),
        ],
    },
    {
        "key": "reg-o",
        "label": "Regulation O (12 CFR 215.4(b))",
        "regime": "reg-o",
        # Resolved live from the passage's own effective_date -- see
        # resolve_regime_versions(). The literal here is a fallback/sanity
        # value only; the live value is what actually gets written.
        "effective_from": "2026-01-01",
        "effective_to": None,  # still in force
        "limit_pct_of_capital": None,
        "limit_absolute_usd": 500_000.0,
        "citations": [
            ("reg-o", "215.4(b)(2)", None, "$500,000", "states the $500,000 absolute cap"),
        ],
    },
]


def resolve_regime_versions() -> list[dict]:
    """Resolve every citation live and fold in the real effective_date.

    Fails loudly (FATAL, exit 2) rather than writing a RegimeVersion with a
    citation that does not actually resolve or does not actually contain
    the text it is cited for -- the brief's own rule: "A RegimeVersion node
    with no ex:citesProvision ... is a load failure, not a warning."
    """
    db = mongo_db(write=False)
    out: list[dict] = []
    for rv in REGIME_VERSIONS:
        resolved_citations: list[dict] = []
        live_effective_from = rv["effective_from"]
        # Minor 4: True only when `live_effective_from` below gets
        # overwritten with the eCFR retrieval date rather than a genuine
        # commencement date -- see the module docstring's "Regulation O's
        # effective-from date" section for why Reg O is the one regime this
        # happens to.
        effective_from_is_retrieval_snapshot = False
        for citation_regime, provision, document_id, must_contain, role in rv["citations"]:
            query = {"regime": citation_regime, "provision": provision}
            if document_id:
                query["document_id"] = document_id
            row = db.passage.find_one(query)
            if row is None:
                print(f"FATAL: no {citation_regime!r} passage for provision "
                      f"{provision!r} (document_id={document_id!r}) -- "
                      "Task 4/load_regime_mongo.py must run first.")
                sys.exit(2)
            if must_contain not in row["text"]:
                print(f"FATAL: {citation_regime}/{provision} no longer contains "
                      f"{must_contain!r} -- the provision label may have "
                      "drifted to a different paragraph. Not citing an "
                      "unverified passage.")
                sys.exit(2)
            resolved_citations.append({
                "regime": citation_regime,
                "provision": provision,
                "passage_id": row["passage_id"],
                "document_id": row["document_id"],
                "role": role,
                "first_line": row["text"].strip().splitlines()[0][:160],
            })
            # Reg O's effective_from is the eCFR "as of" date actually
            # fetched, read from the passage itself rather than hard-coded
            # -- a retrieval date, not the $500,000 cap's real commencement
            # date (which has stood for decades). Flagged rather than left
            # to look like CRR/PRA's genuine effective dates.
            if rv["regime"] == "reg-o" and row.get("effective_date"):
                live_effective_from = row["effective_date"]
                effective_from_is_retrieval_snapshot = True
        resolved = dict(rv)
        resolved["effective_from"] = live_effective_from
        resolved["effective_from_is_retrieval_snapshot"] = effective_from_is_retrieval_snapshot
        resolved["citations"] = resolved_citations
        resolved["provenance"] = REG_PROVENANCE
        out.append(resolved)
    return out


# --------------------------------------------------------------------------
# Part 2 — internal appetite, re-derived live against Fluree + Postgres
# --------------------------------------------------------------------------

def entity_uri_to_lei() -> dict[str, str]:
    q = f"SELECT ?s ?l FROM <{L}> WHERE {{ ?s <{EX}lei> ?l }}"
    out: dict[str, str] = {}
    for b in fluree.query(q)["results"]["bindings"]:
        out[b["s"]["value"]] = b["l"]["value"]
    return out


def _components(predicates: list[str]) -> tuple[dict[str, str], "callable"]:
    """Union-find over the named predicates -- Task 7's brief script,
    reused verbatim (`FILTER(?s = ?o)` isn't needed here: these predicates
    never relate a node to itself in this estate, and the loop only ever
    compares parent pointers, not raw triples)."""
    par: dict[str, str] = {}

    def find(x: str) -> str:
        par.setdefault(x, x)
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    for p in predicates:
        q = f"SELECT ?a ?b FROM <{L}> WHERE {{ ?a <{EX}{p}> ?b }}"
        for r in fluree.query(q)["results"]["bindings"]:
            a, b = find(r["a"]["value"]), find(r["b"]["value"])
            if a != b:
                par[a] = b
    return par, find


def derive_group_exposures() -> dict:
    """Recompute, from the live stores, the numbers the appetite level
    depends on -- never trust a prior report's figures for a decision this
    load-bearing (Wave 19's own instruction: "re-derive it yourself").

    Returns the top group under 'control' basis (connectedTo only) and
    under 'both' basis (connectedTo + economicallyDependentOn), plus the
    two Task 7 singletons (TransDigm alone, TransDigm+Vertiv merged) needed
    to place the appetite inside the consequential band.
    """
    uri_to_lei = entity_uri_to_lei()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT borrower_lei, SUM(commitment_amount) '
                    f'FROM "{S}".facility '
                    f'WHERE borrower_lei IS NOT NULL '
                    f'GROUP BY borrower_lei')
        exposure_by_lei = {lei: float(amt) for lei, amt in cur.fetchall()
                            if amt is not None}
        cur.execute(f'SELECT tier1_capital, unit FROM "{S}".bank_capital '
                    f'ORDER BY report_date DESC LIMIT 1')
        tier1_row = cur.fetchone()

    if tier1_row is None:
        print("FATAL: no bank_capital row -- run loaders/load_reporting_bank.py first.")
        sys.exit(2)
    tier1_amount, tier1_unit = tier1_row
    tier1_usd = float(tier1_amount) * (1000 if tier1_unit == "USD_THOUSANDS" else 1)

    def group_exposures(predicates: list[str]) -> tuple[dict[str, float], "callable"]:
        par, find = _components(predicates)
        totals: defaultdict[str, float] = defaultdict(float)
        for uri, lei in uri_to_lei.items():
            amt = exposure_by_lei.get(lei)
            if not amt:
                continue
            root = find(uri) if uri in par else uri
            totals[root] += amt
        return dict(totals), find

    control_totals, control_find = group_exposures(["connectedTo"])
    both_totals, both_find = group_exposures(["connectedTo", "economicallyDependentOn"])

    # Resolve TransDigm's and Vertiv's own LEIs directly rather than by
    # searching sorted totals -- these are Task 7's own named entities, not
    # "whichever group happens to rank second."
    transdigm_lei = "549300EQD0ZXRSMG3549"
    vertiv_lei = "549300KTTIRAOGXCRV69"
    uri_by_lei = {lei: uri for uri, lei in uri_to_lei.items()}

    transdigm_alone_pct = control_totals[control_find(uri_by_lei[transdigm_lei])] / tier1_usd * 100
    merged_pct = both_totals[both_find(uri_by_lei[vertiv_lei])] / tier1_usd * 100
    largest_control_pct = max(control_totals.values()) / tier1_usd * 100

    return {
        "tier1_usd": tier1_usd,
        "largest_control_group_pct": largest_control_pct,
        "transdigm_alone_pct": transdigm_alone_pct,
        "transdigm_vertiv_merged_pct": merged_pct,
    }


def verify_appetite_placement(derived: dict, appetite_pct: float) -> list[str]:
    """Both conditions the brief names, checked against LIVE numbers, not
    the brief's own figures. Returns a list of failures (empty = OK)."""
    failures = []
    if not (appetite_pct < derived["largest_control_group_pct"]):
        failures.append(
            f"appetite {appetite_pct}% does not sit below the largest "
            f"control-basis group ({derived['largest_control_group_pct']:.4f}%) "
            "-- job 1 (real group breaches house policy) would not hold")
    if not (derived["transdigm_alone_pct"] < appetite_pct <= derived["transdigm_vertiv_merged_pct"]):
        failures.append(
            f"appetite {appetite_pct}% is not inside "
            f"({derived['transdigm_alone_pct']:.4f}%, "
            f"{derived['transdigm_vertiv_merged_pct']:.4f}%] -- job 2 (the "
            "economicallyDependentOn edge changes which limit binds) "
            "would not hold")
    return failures


def build() -> dict:
    regime_versions = resolve_regime_versions()
    derived = derive_group_exposures()
    failures = verify_appetite_placement(derived, INTERNAL_APPETITE_PCT)
    if failures:
        print("FATAL: the proposed internal appetite does not satisfy its "
              "own design conditions, measured live:")
        for f in failures:
            print(f"  - {f}")
        print("Not writing an artifact with a number that fails its own check.")
        sys.exit(2)

    internal_appetite = {
        "key": "internal-appetite",
        "label": "Internal large-exposure appetite",
        "limit_pct_of_capital": INTERNAL_APPETITE_PCT,
        "limit_absolute_usd": None,
        "effective_from": INTERNAL_APPETITE_EFFECTIVE_FROM,
        "effective_to": None,
        "governed_by_regime": "pra-2022",  # the live regulatory regime this house policy operates alongside
        "provenance": INTERNAL_PROVENANCE,
        "derivation": derived,
    }
    return {"regime_versions": regime_versions, "internal_appetite": internal_appetite}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = build()

    print("Wave 19 Task 9 — limit envelope and regime version history\n")
    for rv in doc["regime_versions"]:
        print(f"  {rv['label']}")
        snapshot_note = (" [retrieval snapshot, not a commencement date]"
                         if rv.get("effective_from_is_retrieval_snapshot") else "")
        print(f"    {rv['effective_from']}{snapshot_note} -> {rv['effective_to'] or '(open)'}"
              f"   limit={rv['limit_pct_of_capital']}%"
              f" abs=${rv['limit_absolute_usd'] or 0:,.0f}")
        for c in rv["citations"]:
            print(f"    cites {c['regime']}/{c['provision']} ({c['passage_id']}) "
                  f"-- {c['role']}")
            print(f"      \"{c['first_line']}\"")

    d = doc["internal_appetite"]["derivation"]
    print(f"\n  internal appetite     {doc['internal_appetite']['limit_pct_of_capital']}%")
    print(f"    tier1 (live)          ${d['tier1_usd']:,.0f}")
    print(f"    largest control group {d['largest_control_group_pct']:.4f}%  (must exceed appetite)")
    print(f"    TransDigm alone       {d['transdigm_alone_pct']:.4f}%  (must be below appetite)")
    print(f"    TransDigm+Vertiv both {d['transdigm_vertiv_merged_pct']:.4f}%  (appetite must be <= this)")

    if args.dry_run:
        print("\n  [dry-run] artifact not written")
        return 0

    SCREEN.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(f"\n  wrote {ARTIFACT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
