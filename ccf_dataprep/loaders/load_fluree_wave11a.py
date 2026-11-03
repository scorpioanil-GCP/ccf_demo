#!/usr/bin/env python3
"""Wave 11a Task 8 — load the rating-and-spread-migration graph into Fluree.

Per §C: Postgres owns observations and policy (`E`, `P` — Task 7, already
loaded); Fluree owns the event and assertion history (`R`, `T`). This loader
is that second half: instrument nodes, `issuedBy` edges, the grade-assertion
supersession chain, and the public issuance / rating-action events.

**Single-writer discipline, checked against what Postgres already holds, not
assumed.** `debt_instrument.coupon_pct`, `.maturity`, `.face_amount_usd`,
`.rating_band`, `.seniority`, `.tenor_years` and `rating_scale.notch` /
`.rating_band` / `.modifier` are all Postgres columns as of Task 7. None of
them appear as a Fluree literal below — an instrument node here carries only
its two types and a label; a grade-assertion node never carries a notch or a
band, because both are one join away from the `grade` string it does carry
(`rating_scale.grade -> notch/band/modifier`, policy-versioned).

**`grade` itself is not a leak.** Nothing in Postgres records which grade an
obligor held on a given date — Task 7 deliberately loaded only the static
15-row scale (grade -> notch), not the 245-row assertion history. Fluree is
the assertion history's only home, by design (§D step 3: "the migration IS
the supersession chain, which is why this product needs a ledger rather than
a current-state table"). So each assertion node carries `ex:grade`,
`ex:validFrom` / `ex:validTo`, `ex:assertedAt`, `ex:trigger` and
`ex:provenance` — the same shape Wave 5 used for amendments and breaches,
where the ledger is the sole author of the fact rather than a mirror of one.

## Bindings verified live against spec.edmcouncil.org, 2026-08-19

`issuedBy` and a credit-grade / market-observation class were unbound going
into this task (§3.2 of docs/wave11a-design.md). Resolved by fetching the
Production RDF/XML modules directly (not guessed from module names — module
membership does not pin an IRI):

    issuedBy            -> fibo-fnd-rel-rel:isIssuedBy       REAL FIBO term
                            (FND/Relations/Relations — prefix already bound,
                            Wave 8, for hasIdentity/isIdentifiedBy/controls)
    credit-grade class  -> fibo-fbc-dae-crt:OrganizationCreditRating
                            REAL FIBO term (FBC/DebtAndEquities/CreditRatings,
                            subclass of CreditRating -> fibo-fnd-arr-rt:Rating
                            -> Opinion). Used over InstrumentCreditRating
                            because Task 6's grade chain rates the OBLIGOR
                            (keyed by lei), not an instrument.
    market observation  -> fibo-fnd-arr-rt:RatingAssessmentEvent REAL FIBO
                            term (FND/Arrangements/Ratings — "individual
                            assessment resulting in a grade or score", exactly
                            the shape of a confirmed agency rating action
                            found in a real 8-K)

Two new prefixes added to the binding table:
`fibo-fbc-dae-crt` (FBC/DebtAndEquities/CreditRatings/) and
`fibo-fnd-arr-rt` (FND/Arrangements/Ratings/). See
docs/ccf_dataprep_v2.md, "Wave 11a extension" — **the vault mirror needs
refreshing** for these two prefixes, the two classes, and `isIssuedBy`.

The edge from a rating node to the party it concerns
(`fibo-fbc-dae-crt:concernsParty`) is reused for BOTH `OrganizationCreditRating`
and `RatingAssessmentEvent`: the Assessments module (RatingAssessmentEvent's
ultimate ancestor) has no generic subject-party property of its own, and
`concernsParty` is explicitly `subPropertyOf cmns-pts:hasParty` — the
CreditRatings module's own general-purpose party link, not scoped to one
class in its restrictions.

**One `ex:` extension, not two.** An Item 2.03 debt-issuance disclosure has no
Production-ontology class — the only FIBO vocabulary for a securities issuance
*event* lives in `BP/SecuritiesIssuance/DebtIssuance`, which is FIBO
**Business Process**, out of scope for the same reason `abs-securitization-
surveillance`'s `Securitization` search landed on `ex:` in Wave 8: Production
models the instrument, not the bank's-eye-view disclosure event. So:
`ex:IssuanceEvent` (class) and `ex:filedBy` (property, event -> obligor).

## `--reconcile`

Same shape as `load_fluree_wave10.py`. This loader writes four edge
predicates — `isIssuedBy`, `concernsParty`, `supersededBy`, `filedBy` — and
`--reconcile` retracts its own edges on them before rebuilding, so a re-load
against regenerated JSON replaces rather than appends.

**Corrected 2026-08-21 (Wave 11b Task 13).** This section previously read
"this loader owns four edge predicates outright … `--reconcile` retracts
every edge on them", and the code matched: a blind, predicate-wide
`DELETE DATA` of every edge found on all four. That was accurate on
2026-08-19 and was falsified two days later, when `load_fluree_wave11b.py`
began asserting 535 `ex:supersededBy` edges of its own (486 `sig-8k-*`,
49 `prior-obs-*`) beside this loader's 215 `syn-g-*`. A real (non-dry-run)
`--reconcile` would have retracted all 750 and rebuilt only 215, orphaning
Wave 11b's supersession chain irrecoverably — Fluree is append-only, so the
retraction is itself a commit and the current-state data is simply gone.

Retraction is now scoped by SUBJECT to the URIs this loader mints
(`my_node_uris()`), the pattern `load_fluree_wave11b.py` established and
proved. All four predicates are scoped that way, including the three still
exclusive to this loader — the assumption that failed was "no one else will
ever write this predicate", so it is no longer relied on anywhere here.

Nodes stay out of scope for RETRACTION of their literals, as in Wave 10: this
run's node URIs are deterministic functions of the JSON's own ids (`syn-i-*`,
`syn-g-*`, `{accession}`), so a re-run against UNCHANGED source JSON reasserts
the same node triples (a no-op) rather than duplicating them. A regenerated
JSON with new random ids would leave the old nodes orphaned rather than
corrected — the same node-lifecycle gap Wave 10 accepted and documented, not
solved here either.

**The whole trade the subject-scoping fix makes, not just the half that
improves.** Scoping by subject removed a cross-wave data-loss hazard and, in
the same move, WIDENED that node-lifecycle gap to cover EDGES, which it did not
cover before. The blind predicate scan retracted every edge on the four
predicates regardless of whose subject it hung off, so a stale edge whose id
had fallen out of the artifact was still swept up; a subject-scoped retraction
cannot see it, because `node_uris` is built from the ids the CURRENT artifact
names. Concretely: two of the four id families are SEED-derived —
`mint_assertion_id()` is `sha256(f"{SEED}|grade|{lei}|{seq}")`
(`generators/generate_grades.py`) and `mint_instrument_id()` is the same shape
(`generate_instruments.py`, `SEED = 20260817`). Regenerate either artifact under
a DIFFERENT seed and every id changes, so the old `syn-g-*` / `syn-i-*` edges
fall outside `node_uris` and survive `--reconcile` unretracted, beside the
freshly-inserted ones. The other two families (`issuance-{accession}`,
`rating-action-{accession}`) are keyed on EDGAR accession numbers and are not
exposed to this at all.

Accepted deliberately, and it is not close: the gap is hypothetical (it needs a
seed change, which nothing in the pipeline does — `SEED` is a module constant
precisely so it does not drift) and it is LOUD when it fires (orphaned edges are
visible to `partition.py`'s dangling check and to
`artifact_reproduces_store.py`'s content comparison). The hazard it replaced was
live, silent, and irreversible. **A narrow, documented idempotency gap beats
cross-wave data loss** — but the next reader should see the whole trade rather
than only the half that improves. If a seed ever does change, retract by subject
using the OLD artifact first, then regenerate: `reconcile()` can only ever
retract what some artifact still names.

## Resolve, never construct

Every edge target is `entity_uri_by_lei()` — the node Wave 3 actually
created — never a constructed `ex:{lei}` URI. Checked live before writing a
single triple: all 30 instrument/grade obligor LEIs, all 50 issuance LEIs,
and all 4 rating-action LEIs already resolve. `dangling` reports zero as a
consequence of that check, not an assumption.

    uv run loaders/load_fluree_wave11a.py --dry-run
    uv run loaders/load_fluree_wave11a.py
    uv run loaders/load_fluree_wave11a.py --reconcile --dry-run
    uv run loaders/load_fluree_wave11a.py --reconcile
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, REPO_ROOT, pg_connect
from loaders.load_collateral_wave9 import entity_uri_by_lei, triple, uri

SCREEN = REPO_ROOT / "sources" / "screening"
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"

# --- Real FIBO bindings — already in the contract (Wave 8) --------------
C_DEBT_INSTRUMENT = f"{FIBO}FBC/FinancialInstruments/FinancialInstruments/DebtInstrument"
C_CORPORATE_BOND = f"{FIBO}SEC/Debt/Bonds/CorporateBond"

# --- Real FIBO bindings — verified live in this task, added to the contract
C_CREDIT_RATING = f"{FIBO}FBC/DebtAndEquities/CreditRatings/CreditRating"
C_ORGANIZATION_CREDIT_RATING = (
    f"{FIBO}FBC/DebtAndEquities/CreditRatings/OrganizationCreditRating"
)
C_RATING_ASSESSMENT_EVENT = f"{FIBO}FND/Arrangements/Ratings/RatingAssessmentEvent"

P_IS_ISSUED_BY = f"{FIBO}FND/Relations/Relations/isIssuedBy"
P_CONCERNS_PARTY = f"{FIBO}FBC/DebtAndEquities/CreditRatings/concernsParty"

# --- ex: extension — FIBO Production has no issuance-DISCLOSURE-event class
C_ISSUANCE_EVENT = f"{EX}IssuanceEvent"
P_FILED_BY = f"{EX}filedBy"

# --- declared since Wave 5, populated here for the first time ------------
P_SUPERSEDED_BY = f"{EX}supersededBy"

BATCH = 500

#: The four edge predicates this loader writes.
#:
#: **It is NOT the sole author of all four.** It was, when this file was
#: written on 2026-08-19 — and `--reconcile` accordingly retracted every edge
#: on each of them by a blind predicate-wide scan. Wave 11b falsified that on
#: 2026-08-21: `loaders/load_fluree_wave11b.py` now asserts 535 more
#: `ex:supersededBy` edges (486 on `sig-8k-*` subjects, 49 on `prior-obs-*`),
#: alongside this loader's 215 on `syn-g-*`. A blind retraction here would
#: have deleted all 750 and rebuilt only its own 215, orphaning Wave 11b's
#: chain — permanently, because Fluree is append-only and the retraction
#: itself is a recorded commit.
#:
#: So `--reconcile` is scoped by SUBJECT, exactly as
#: `load_fluree_wave11b.py`'s own `reconcile()` is: only triples whose
#: subject is a URI THIS loader mints are retracted. See `my_node_uris()`.
#: `isIssuedBy`, `concernsParty` and `filedBy` remain exclusive to this
#: loader today, but they are scoped the same way rather than relying on
#: that staying true — which is the assumption that failed the first time.
OWNED_PREDICATES = {
    "isIssuedBy": P_IS_ISSUED_BY,
    "concernsParty": P_CONCERNS_PARTY,
    "supersededBy": P_SUPERSEDED_BY,
    "filedBy": P_FILED_BY,
}


def load(name: str) -> dict:
    return json.loads((SCREEN / name).read_text())


def my_node_uris(instrument_ids: set[str], assertion_ids: set[str],
                 issuance_accessions: set[str],
                 action_accessions: set[str]) -> set[str]:
    """The exact set of node URIs this loader mints, and therefore the only
    subjects `--reconcile` may retract from.

    Four families, each a deterministic function of an id this loader's own
    source artifacts carry: `syn-i-*` instruments (from Postgres
    `debt_instrument`), `syn-g-*` grade assertions (`wave11a_grades.json`),
    `issuance-{accession}` (`wave11a_issuance.json`) and
    `rating-action-{accession}` (`wave11a_rating_actions.json`).

    Nothing else in the estate constructs a URI in any of those four
    families; Wave 11b's own nodes are `8k-*`, `sig-*` and `prior-obs-*`,
    disjoint from all four.
    """
    uris = {uri(i) for i in instrument_ids}
    uris |= {uri(a) for a in assertion_ids}
    uris |= {uri(f"issuance-{a}") for a in issuance_accessions}
    uris |= {uri(f"rating-action-{a}") for a in action_accessions}
    return uris


def _asserted_edges(predicate: str) -> list[tuple[str, str]]:
    """(subject, object) for every currently-asserted edge on `predicate`,
    anywhere in the ledger — filtered to OUR subjects by the caller, never
    trusted as ours just because the predicate matches."""
    q = f"SELECT ?s ?o FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s <{predicate}> ?o }}"
    return [(b["s"]["value"], b["o"]["value"])
            for b in fluree.query(q).get("results", {}).get("bindings", [])]


def reconcile(*, dry_run: bool, node_uris: set[str]) -> int:
    """Retract this loader's own edges — scoped by SUBJECT — then rebuild.

    Wave 10's lesson, built in from the start rather than discovered after a
    regenerated JSON appended corrected edges beside stale ones: Fluree is
    append-only and this loader is INSERT DATA only, so a plain re-load is
    additive, not corrective.

    **Scoped by subject since 2026-08-21 (Wave 11b Task 13).** The original
    version scanned each owned predicate ledger-wide and retracted every edge
    it found, on the strength of a docstring claim that this loader was "the
    sole author" of all four. That was true when written and false three days
    later: `load_fluree_wave11b.py` writes 535 `ex:supersededBy` edges of its
    own. A blind run would have retracted all 750 and rebuilt 215 — deleting
    another wave's supersession chain with no error and no way back, since
    the retraction is itself an append-only commit.

    Retraction is therefore filtered to subjects in `node_uris`
    (`my_node_uris()`), which is why `main()` now reads the artifacts BEFORE
    reconciling rather than after: the safe scope is a function of the
    artifacts, so it cannot be computed before they are in hand.

    Literals are still out of scope here, matching this loader's original
    contract — see the module docstring's `--reconcile` section. Wave 11b's
    loader retracts literals too; this one is not being widened in the same
    change that fixes a data-loss hazard.

    **Read the module docstring's paragraph on what this trade costs before
    editing this function.** Subject scoping is not free: it extends the
    existing node-lifecycle gap to EDGES, so an id that falls out of the
    artifact (a regeneration under a different `SEED` is the realistic route,
    since `syn-g-*` and `syn-i-*` are both `sha256(SEED|…)`) leaves its edges
    unretracted where the old blind scan would have swept them up. Hypothetical,
    loud when it fires, and a far better trade than the silent cross-wave
    deletion it replaced — but it is a trade, not a pure win.
    """
    total = 0
    statements: list[str] = []
    for name, pred in OWNED_PREDICATES.items():
        pairs = [(s, o) for s, o in _asserted_edges(pred) if s in node_uris]
        others = len(_asserted_edges(pred)) - len(pairs)
        note = f"  ({others} on other loaders' subjects, left alone)" if others else ""
        print(f"    {name:<15} {len(pairs):>5} asserted (ours){note}")
        statements += [f"<{s}> <{pred}> <{o}> ." for s, o in pairs]
        total += len(pairs)

    if not statements:
        print("    nothing asserted — nothing to retract")
        return 0
    print(f"    {total} edges to retract")
    if dry_run:
        print("    [dry-run] nothing retracted")
        return 0

    for i in range(0, len(statements), BATCH):
        fluree.update("DELETE DATA {\n" + "\n".join(statements[i:i + BATCH]) + "\n}")

    remaining = sum(
        len([1 for s, _ in _asserted_edges(p) if s in node_uris])
        for p in OWNED_PREDICATES.values()
    )
    print(f"    retracted · edges remaining on our own subjects: {remaining}")
    if remaining:
        print("    WARNING — retraction incomplete; not proceeding to the rebuild.")
    return remaining


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reconcile", action="store_true",
                    help="retract every edge this loader owns before rebuilding. "
                         "Required when the source JSON has been regenerated — "
                         "without it a re-load appends beside the stale edges "
                         "rather than replacing them, because Fluree is append-only.")
    args = ap.parse_args()

    entity_uri = entity_uri_by_lei()
    print(f"  resolved {len(entity_uri)} entity nodes from the ledger")

    # Instruments come from Postgres — the authoritative, already-loaded copy
    # (Task 7), not the JSON staging artifact. Read-only: a SELECT, no write.
    S = PG_SCHEMA_V2
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT instrument_id, lei FROM "{S}".debt_instrument')
        instruments = cur.fetchall()

    grades_doc = load("wave11a_grades.json")
    issuance_doc = load("wave11a_issuance.json")
    actions_doc = load("wave11a_rating_actions.json")

    assertions = grades_doc["assertions"]
    issuance = issuance_doc["issuance"]
    confirmed_actions = [r for r in actions_doc["rating_actions"] if r.get("confirmed")]
    assertion_ids = {a["assertion_id"] for a in assertions}

    # --reconcile runs AFTER the artifacts are read, not before: the safe
    # retraction scope is a function of the ids those artifacts carry. See
    # reconcile()'s docstring for why a blind predicate scan is unsafe.
    if args.reconcile:
        node_uris = my_node_uris(
            {i for i, _ in instruments},
            assertion_ids,
            {r["accession"] for r in issuance},
            {r["accession"] for r in confirmed_actions},
        )
        print("  --reconcile: retracting this loader's own edges "
              f"({len(node_uris)} node URIs in scope) before rebuild")
        if reconcile(dry_run=args.dry_run, node_uris=node_uris):
            return 1

    triples: list[str] = []

    # T-box for the one ex: extension. Real FIBO classes reused below are
    # not re-declared here, per the Wave 10 precedent this loader follows.
    triples.append(triple(C_ISSUANCE_EVENT, RDF_TYPE, OWL_CLASS))
    triples.append(triple(
        C_ISSUANCE_EVENT, RDFS_LABEL,
        "IssuanceEvent (ex: extension — FIBO Production has no issuance "
        "disclosure-event class; BP/SecuritiesIssuance/DebtIssuance is "
        "Business Process, out of scope)", literal=True))

    # --- instrument nodes + issuedBy ---------------------------------------
    instrument_dangling = 0
    for instrument_id, lei in instruments:
        node = uri(instrument_id)
        triples += [
            triple(node, RDF_TYPE, C_DEBT_INSTRUMENT),
            triple(node, RDF_TYPE, C_CORPORATE_BOND),
            triple(node, RDFS_LABEL, instrument_id, literal=True),
        ]
        target = entity_uri.get(lei)
        if target is None:
            instrument_dangling += 1
            continue
        triples.append(triple(node, P_IS_ISSUED_BY, target))

    # --- grade assertions: the supersession chain --------------------------
    grade_dangling = 0
    supersedes_dangling = 0
    for a in assertions:
        node = uri(a["assertion_id"])
        triples += [
            triple(node, RDF_TYPE, C_CREDIT_RATING),
            triple(node, RDF_TYPE, C_ORGANIZATION_CREDIT_RATING),
            triple(node, RDFS_LABEL,
                   f"{a['grade']} grade — {a['lei']} from {a['valid_from']}",
                   literal=True),
            triple(node, f"{EX}grade", a["grade"], literal=True),
            triple(node, f"{EX}validFrom", a["valid_from"], literal=True),
            triple(node, f"{EX}assertedAt", a["asserted_at"], literal=True),
            triple(node, f"{EX}trigger", a["trigger"], literal=True),
            triple(node, f"{EX}provenance", a["provenance"], literal=True),
        ]
        if a["valid_to"]:
            triples.append(triple(node, f"{EX}validTo", a["valid_to"], literal=True))

        target = entity_uri.get(a["lei"])
        if target is None:
            grade_dangling += 1
        else:
            triples.append(triple(node, P_CONCERNS_PARTY, target))

        if a["supersedes"]:
            if a["supersedes"] not in assertion_ids:
                supersedes_dangling += 1
            else:
                triples.append(triple(uri(a["supersedes"]), P_SUPERSEDED_BY, node))

    # --- issuance events: Item 2.03 filings ---------------------------------
    issuance_dangling = 0
    for r in issuance:
        node = uri(f"issuance-{r['accession']}")
        triples += [
            triple(node, RDF_TYPE, C_ISSUANCE_EVENT),
            triple(node, RDFS_LABEL,
                   f"Item 2.03 filing {r['accession']} ({r['file_date']})",
                   literal=True),
            triple(node, f"{EX}validFrom", r["file_date"], literal=True),
            triple(node, f"{EX}sourceAccession", r["accession"], literal=True),
            triple(node, f"{EX}provenance", r["provenance"], literal=True),
        ]
        target = entity_uri.get(r["lei"])
        if target is None:
            issuance_dangling += 1
            continue
        triples.append(triple(node, P_FILED_BY, target))

    # --- rating-action events: confirmed public agency actions -------------
    action_dangling = 0
    for r in confirmed_actions:
        node = uri(f"rating-action-{r['accession']}")
        triples += [
            triple(node, RDF_TYPE, C_RATING_ASSESSMENT_EVENT),
            triple(node, RDFS_LABEL,
                   f"Rating action reported in {r['accession']} ({r['file_date']})",
                   literal=True),
            triple(node, f"{EX}validFrom", r["file_date"], literal=True),
            triple(node, f"{EX}sourceAccession", r["accession"], literal=True),
            triple(node, f"{EX}provenance", r["provenance"], literal=True),
            triple(node, f"{EX}evidence", r["evidence"], literal=True),
        ]
        target = entity_uri.get(r["lei"])
        if target is None:
            action_dangling += 1
            continue
        triples.append(triple(node, P_CONCERNS_PARTY, target))

    dangling = (instrument_dangling + grade_dangling + supersedes_dangling
                + issuance_dangling + action_dangling)

    print("Wave 11a Task 8 — Fluree load\n")
    print(f"  instruments        {len(instruments):>6}  "
          f"(dangling issuedBy: {instrument_dangling})")
    print(f"  grade assertions    {len(assertions):>6}  "
          f"(dangling concernsParty: {grade_dangling}, "
          f"dangling supersedes: {supersedes_dangling})")
    print(f"  issuance events     {len(issuance):>6}  "
          f"(dangling filedBy: {issuance_dangling})")
    print(f"  rating actions      {len(confirmed_actions):>6}  "
          f"(dangling concernsParty: {action_dangling})")
    print(f"  total triples       {len(triples):>6}")
    print(f"  dangling (total)    {dangling:>6}")
    if dangling:
        print("  NOTE: skipped rather than pointed at a constructed URI. "
              "A constructed URI cannot fail loudly — see Wave 9.")

    n_super = sum(1 for a in assertions if a["supersedes"])
    print(f"\n  assertions carrying a supersedes pointer: {n_super} "
          f"(this run asserts {n_super} ex:supersededBy edges on syn-g-* "
          f"subjects; Wave 11b's 535 on sig-8k-*/prior-obs-* are not touched)")

    if args.dry_run:
        print("\n  [dry-run] nothing written to Fluree")
        return 0

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")
    print(f"\n  ledger now at t={fluree.ledger_t()} · "
          f"{fluree.count_triples():,} triples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
