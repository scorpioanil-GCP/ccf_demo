#!/usr/bin/env python3
"""Wave 16 Task 12 -- opportunity signals and coverage/comparability edges,
into Fluree.

`generators/generate_opportunity_signals.py` already assembled the flat
1,270-row ledger at `sources/screening/wave16_signals.json`. Nothing in
Postgres stores that ledger (`loaders/load_postgres_wave16.py` owns
perspectives, weight vectors and mandates -- not the raw signal rows), so
Fluree is this data's only home, and this loader is the one place it becomes
a graph a temporal traversal can walk.

## Node IRIs

One `ex:OpportunitySignal` per signal: `http://example.org/fibo/OPPSIG-{signal_id}`.
Deterministic from the artifact's own `signal_id`, so a rerun mints the same
subjects and a plain re-run (no flag) is idempotent by construction --
INSERT DATA of a triple already in the ledger is a no-op.

## Type explicitly (rule 7 / CLAUDE.md)

Fluree runs without reasoning, so a query for `ex:OpportunitySignal` returns
only nodes explicitly typed as one. Every one of the 1,270 nodes carries
`rdf:type ex:OpportunitySignal` -- there is no superclass to lean on.

## All dates are plain strings

Fluree 4.1.4 corrupts a typed date literal on write (known-issues.md
section 19.4): a date inserted with the XSD date datatype reads back as a
transaction-derived value climbing a couple of days per insert, not the date
that was written. Plain-string dates round-trip exactly, so `observed_at`
and `asserted_at` are asserted as bare quoted strings and this file contains
no datatype suffix anywhere, on any literal. `validators/test_ib_rank.py`
asserts this file's own source text stays that way, and
`loaders/dump_fluree.py` asserts the LEDGER stays that way after every load.

## Load ALL 1,270 signals, mark supersession, never filter to current

916 signals are current and 354 are superseded, and the ledger is the
history -- every one of the 1,270 gets a node. `ex:isCurrent` carries the
artifact's own "true"/"false" as a plain string (not a typed boolean, per
the rule above) so a current-value query can filter without losing the
354 superseded rows from the graph entirely. Supersession itself reuses the
estate's existing `ex:supersededBy` edge (Waves 5, 11a, 11b, 12): the OLDER
signal named in a row's `supersedes` field gets `ex:supersededBy` pointing
at the NEWER row, matching the "v1 supersededBy v2" direction every other
wave already uses.

## Predicate reuse vs new terms

`ex:validFrom` (valid time -- Waves 5/7/11a/11b/14) and `ex:assertedAt`
(assertion time -- same waves) are reused, NOT redeclared, for
`observed_at`/`asserted_at`: the semantics match exactly and a second
spelling of the same bitemporal axis is the mistake Wave 14's design note
already warned against. `ex:provenance` and `ex:signalAbout` are likewise
reused (the latter already carries 595 assertions from Waves 10/11b/11c on
DIFFERENT subjects -- a signal_event/PriorObservation node never named
`OPPSIG-*`, so there is no subject collision).

`ex:signalType` and `ex:observedAt` are NOT used here even though they read
naturally: both are POSTGRES_OWNED_ATTRS in `validators/partition.py`,
claimed by Wave 11b's `signal_event.signal_type` / `signal_event.observed_at`
columns. Asserting either as a Fluree literal would make partition.py report
a real cross-wave predicate-name collision as a single-writer leak -- exactly
the trap `load_fluree_wave12_fx.py`'s RULING F23 already hit and fixed once
for `observedAt` itself. `ex:magnitude`, `ex:isCurrent`, `ex:coveredBy`,
`ex:comparableTo` and `ex:comparabilityBasis` are genuinely new and are
bound in `docs/ccf_dataprep_v2.md` (verified absent from FIBO's dev
quickstart via `ccf.fibo.fibo_absent`, before generation) -- `isCurrent` and
`comparabilityBasis` are ADDED to that table by this task; `OpportunitySignal`,
`coveredBy` and `comparableTo` were already bound by Task 10.

## `ex:coveredBy` -- ALL coverage, primacy carried separately (Fix round 1)

Every one of the 150 `coverage_assignment` rows (37 distinct bankers, 50
covered anchors, up to 3 bankers per anchor) gets one `ex:coveredBy` edge,
from its Wave-3 entity node to the SAME `ex:Banker` node
`load_fluree_wave10.py` already minted at
`http://example.org/fibo/banker-{banker_id}` -- resolved by the Postgres
`banker_id` key, never reconstructed from a display name (Task 3's exact
defect, on the graph side this time). The banker node is reused, not
redeclared.

The first cut of this loader asserted only the 50 PRIMARY assignments, on
the reasoning that "coveredBy" meant one banker per prospect. That was
wrong: this product is anchored on the BANKER (`docs/wave16-design.md`
section 1), so a banker's candidate set is resolved by walking `coveredBy`
FROM the banker, and 24 of the 37 bankers hold no primary assignment at
all -- an empty edge set for two-thirds of the roster, for a product whose
whole spec starts from "resolve banker_id to a coverage portfolio."

Primacy is real and still carried, just not as a filter: `ex:primaryBankerId`
is a plain-string literal on the PROSPECT entity node, naming which of its
(possibly several) covering bankers is primary. This is the RDF-clean
equivalent of a literal "on the edge": RDF triples cannot carry a property
that names one SPECIFIC edge among several with the same predicate and
subject without reifying the relationship into its own node, and a prospect
with 3 covering bankers has exactly that shape (3 `coveredBy` edges, only
one primary). A per-subject literal side-steps reification entirely -- a
consumer holding a prospect's entity node reads both "who covers me"
(`coveredBy`, multi-valued) and "who is primary" (`primaryBankerId`,
single-valued) with two direct lookups, no join, no reified node to
traverse. Exactly one `is_primary` row exists per covered LEI (verified
live before choosing this shape), so the literal is never ambiguous.

## `ex:comparableTo` is derived -- shared SIC, size band DISCLOSED not FILTERED (Fix round 1)

No pre-existing pairwise peer edge exists anywhere in the estate:
`peer_cohort` is SIC-level cohort statistics (sic, tag, frame, thinness) and
`peer_entity` is a CIK+SIC membership list -- neither holds a pair (section 10
of `docs/wave16-design.md`). So comparability is computed here, from data
already loaded:

    prospect's SIC        <- legal_entity.sic
    prospect's total size <- SUM(debt_instrument.face_amount_usd), 0 if none

Every prospect still gets a size tercile band (1..3, ties broken by LEI, so
the split is reproducible) -- but the FIRST cut of this loader used the band
as a second grouping key alongside SIC, and that was wrong: the 50 covered
anchors span 40 distinct SICs and only 5 SICs have >= 2 members (6798 with
7, then 7510/3350/7011/2000 with 2 each), so the SIC-only ceiling is 25
pairs -- and splitting a 7-member SIC into 3 size terciles left ~2 per band,
cutting the realized total to 5. For a product whose whole ranking leans on
comparability, that is destroying the graph rather than refining it.

The fix: group by SIC ALONE. Every SIC with >= 2 covered anchors becomes a
fully-connected set of `ex:comparableTo` pairs (25 pairs / 50 directed
edges, 21 of them within SIC 6798), asserted in both directions
(comparability is symmetric -- a traversal starting from either prospect
must find its peers). The size relationship does not disappear -- it moves
INTO the basis string as disclosed information a consumer can filter on
themselves, rather than a silent pre-filter: each directed edge's SUBJECT
carries its own `ex:comparabilityBasis`
(`"shared SIC 6798; size bands 1 vs 3 (peer {other LEI})"`), built and
asserted in the SAME loop iteration as its `comparableTo` triple so the two
can never diverge. "Comparable must be inspectable, not implied" (the
original brief) means DISCLOSE the size relationship, not exclude on it.

A subject can have several `comparableTo` peers with genuinely different
band pairings (a 7-member SIC spans all 3 bands), so -- unlike the
single-group-per-subject design this replaces -- `comparabilityBasis` is no
longer uniform per subject and cannot be reduced to one literal. The peer's
own LEI is embedded in the basis text specifically so that even though
several `comparabilityBasis` values can land on the same subject (one per
peer), no two are ever textually identical -- RDF triples are a SET, so an
accidental duplicate string on the same subject would silently collapse to
one triple and break the 1:1 count this loader's own test asserts
(`test_comparable_to_and_basis_counts_match`).

## Idempotency -- retract-then-assert, scoped by subject IRI

Two subject populations, two predicate lists, per Rule 5:

  SIGNAL_NODE_PREDICATES  -- every predicate this loader asserts on one of
    its OWN `OPPSIG-*` nodes. Nothing else in the estate mints that prefix,
    so for a subject in that set, retracting EVERY predicate in the list is
    safe -- the same shape `load_fluree_wave12_treasury.py` uses for its own
    `POS-*`/`W12-*`/`posture-*` nodes.

  PROSPECT_EDGE_PREDICATES -- `ex:coveredBy`, `ex:comparableTo`,
    `ex:comparabilityBasis`, `ex:primaryBankerId` ONLY, asserted on entity
    nodes this loader does NOT own (Wave 3's cast). Retraction here is
    scoped to BOTH the subject (one of the 50 covered-anchor entity URIs)
    AND the predicate name, so it never touches `ex:lei`, `rdf:type`, or any
    other loader's triples on the same shared node. A blind predicate-wide
    delete on `ex:signalAbout` would take Waves 10/11b/11c's 595 assertions
    with it; this never runs one.

Reconcile is opt-in (`--reconcile`), matching the estate's convention: a
plain re-run against an unchanged artifact is already idempotent because
every subject and every literal is deterministic, so nothing needs
retracting unless the ARTIFACT changed.

    uv run loaders/load_fluree_wave16.py --dry-run
    uv run loaders/load_fluree_wave16.py
    uv run loaders/load_fluree_wave16.py --reconcile --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

from ccf import fluree
from ccf.config import EX, EX_EXTENSION_SCHEMA_NOTE, PG_SCHEMA_V2, REPO_ROOT, pg_connect
from loaders.load_collateral_wave9 import entity_uri_by_lei, triple, uri

SCREEN = REPO_ROOT / "sources" / "screening"
SIGNALS_PATH = SCREEN / "wave16_signals.json"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"

# --- T-box: new, bound in docs/ccf_dataprep_v2.md's Wave 16 section --------
C_OPPORTUNITY_SIGNAL = f"{EX}OpportunitySignal"

# --- reused predicates, NOT redeclared -- see module docstring -------------
P_VALID_FROM = f"{EX}validFrom"          # observed_at (valid time)
P_ASSERTED_AT = f"{EX}assertedAt"        # asserted_at (assertion time)
P_PROVENANCE = f"{EX}provenance"
P_SIGNAL_ABOUT = f"{EX}signalAbout"
P_SUPERSEDED_BY = f"{EX}supersededBy"

# --- new predicates this loader introduces to the ledger --------------------
P_IS_CURRENT = f"{EX}isCurrent"
P_MAGNITUDE = f"{EX}magnitude"
P_COVERED_BY = f"{EX}coveredBy"
P_COMPARABLE_TO = f"{EX}comparableTo"
P_COMPARABILITY_BASIS = f"{EX}comparabilityBasis"
#: New, Fix round 1. A plain-string literal on the PROSPECT node naming its
#: primary covering banker's id -- the RDF-clean stand-in for "a property on
#: one specific coveredBy edge" (see module docstring).
P_PRIMARY_BANKER_ID = f"{EX}primaryBankerId"

P_IS_FIBO_TERM = f"{EX}isFiboTerm"
P_SCHEMA_NOTE = f"{EX}schemaNote"

BATCH = 400
SIZE_BANDS = 3


def signal_uri(signal_id: str) -> str:
    return uri(f"OPPSIG-{signal_id}")


def banker_uri(banker_id: str) -> str:
    """The SAME node `load_fluree_wave10.py` already minted -- reused, not
    redeclared. Resolved by the Postgres key, never a display name."""
    return uri(f"banker-{banker_id}")


# --- predicates by subject population (see module docstring) ---------------
SIGNAL_NODE_PREDICATES = [
    RDF_TYPE, RDFS_LABEL, P_VALID_FROM, P_ASSERTED_AT, P_PROVENANCE,
    P_IS_CURRENT, P_MAGNITUDE, P_SIGNAL_ABOUT, P_SUPERSEDED_BY,
]
PROSPECT_EDGE_PREDICATES = [P_COVERED_BY, P_COMPARABLE_TO, P_COMPARABILITY_BASIS,
                            P_PRIMARY_BANKER_ID]


def load_signals() -> list[dict]:
    return json.loads(SIGNALS_PATH.read_text())["signals"]


def fetch_coverage_assignments(cur) -> list[dict]:
    """ALL 150 (banker, prospect) rows -- Fix round 1, Finding 1. Every one
    becomes a `coveredBy` edge; `is_primary` becomes the `primaryBankerId`
    literal, never a filter on which edges get loaded."""
    S = PG_SCHEMA_V2
    cur.execute(f'''
        SELECT lei, banker_id, is_primary
          FROM "{S}".coverage_assignment
         ORDER BY lei, banker_id
    ''')
    return [{"lei": lei, "banker_id": banker_id, "is_primary": bool(is_primary)}
            for lei, banker_id, is_primary in cur.fetchall()]


def fetch_prospects(cur) -> list[dict]:
    """Every covered anchor's SIC and total debt face amount -- the raw
    material for the SIC (+ disclosed size band) derivation, computed live
    so it can never drift from what Postgres actually holds. One row per
    covered anchor -- SIC and debt totals are entity-level facts, not
    per-assignment ones, so this is independent of `fetch_coverage_assignments`.

    FINAL FIX WAVE, found while re-running this loader after widening
    `coverage_assignment` (blocker 4): `JOIN coverage_assignment ca ON
    ca.lei = le.lei` fans out one row per assignment BEFORE the
    `LEFT JOIN debt_instrument` and `SUM`, so `total_face` was being
    multiplied by however many bankers cover that anchor -- silently
    correct only by accident while every anchor had 1-3 coverage rows, and
    wrong by 15-22x the instant coverage widened. `EXISTS` restricts to
    covered anchors without joining the assignment rows into the
    aggregation at all, so the debt sum is what it always should have
    been: one row per (lei, instrument), summed once.
    """
    S = PG_SCHEMA_V2
    cur.execute(f'''
        SELECT le.lei, le.sic,
               COALESCE(SUM(di.face_amount_usd), 0) AS total_face
          FROM "{S}".legal_entity le
          LEFT JOIN "{S}".debt_instrument di ON di.lei = le.lei
         WHERE le.is_anchor
           AND EXISTS (
                 SELECT 1 FROM "{S}".coverage_assignment ca
                  WHERE ca.lei = le.lei
               )
         GROUP BY le.lei, le.sic
         ORDER BY le.lei
    ''')
    return [{"lei": lei, "sic": sic, "total_face": float(total_face)}
            for lei, sic, total_face in cur.fetchall()]


def assign_size_bands(prospects: list[dict]) -> None:
    """Tercile of total debt face amount, ties broken by LEI. Mutates each
    row in place with `size_band` in 1..SIZE_BANDS. Rank-based, not a fixed
    dollar cutoff, so the split stays balanced regardless of the underlying
    distribution's shape."""
    ranked = sorted(prospects, key=lambda p: (p["total_face"], p["lei"]))
    n = len(ranked)
    for i, p in enumerate(ranked):
        p["size_band"] = 1 + (i * SIZE_BANDS) // n


def comparable_groups(prospects: list[dict]) -> dict[str, list[dict]]:
    """SIC -> prospect rows (carrying their own size_band), restricted to
    groups of >= 2 -- a group of one has no comparability claim to make.

    Fix round 1, Finding 2: grouped by SIC ALONE, not (sic, size_band). The
    size band is still computed and still carried -- just DISCLOSED on the
    basis string per pair rather than used as a second grouping key that
    silently excludes real same-SIC peers."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for p in prospects:
        if not p["sic"]:
            continue  # no SIC, no comparability claim can be derived
        groups[p["sic"]].append(p)
    return {k: sorted(v, key=lambda p: p["lei"])
            for k, v in groups.items() if len(v) >= 2}


def build(signals: list[dict], coverage: list[dict], prospects: list[dict],
          entity_uri: dict[str, str]) -> tuple[list[str], dict]:
    """Compute every triple this loader will assert, deterministically."""
    triples: list[str] = []
    stats = {
        "signals_typed": 0, "signal_about_asserted": 0, "signal_about_dangling": 0,
        "supersession_edges": 0, "current": 0, "superseded": 0,
        "covered_by_asserted": 0, "covered_by_dangling": 0,
        "primary_banker_id_asserted": 0, "distinct_bankers_covered": 0,
        "comparable_pairs": 0, "comparable_prospects": 0,
        "comparable_edges": 0, "comparability_basis_asserted": 0,
    }

    # --- T-box: OpportunitySignal, first materialized here ------------------
    triples += [
        triple(C_OPPORTUNITY_SIGNAL, RDF_TYPE, OWL_CLASS),
        triple(C_OPPORTUNITY_SIGNAL, RDFS_LABEL, "OpportunitySignal", literal=True),
        triple(C_OPPORTUNITY_SIGNAL, P_IS_FIBO_TERM, "false", literal=True),
        triple(C_OPPORTUNITY_SIGNAL, P_SCHEMA_NOTE, EX_EXTENSION_SCHEMA_NOTE,
               literal=True),
    ]

    # --- one OpportunitySignal node per signal, ALL 1,270 of them ----------
    for row in signals:
        node = signal_uri(row["signal_id"])
        is_current = bool(row["is_current"])
        triples += [
            triple(node, RDF_TYPE, C_OPPORTUNITY_SIGNAL),
            triple(node, RDFS_LABEL,
                   f"{row['signal_type']} -- {row['lei']} -- {row['observed_at']}",
                   literal=True),
            triple(node, P_VALID_FROM, row["observed_at"], literal=True),
            triple(node, P_ASSERTED_AT, row["asserted_at"], literal=True),
            triple(node, P_PROVENANCE, row["provenance"], literal=True),
            triple(node, P_IS_CURRENT, "true" if is_current else "false",
                   literal=True),
            triple(node, P_MAGNITUDE, str(row["magnitude"]), literal=True),
        ]
        stats["signals_typed"] += 1
        stats["current" if is_current else "superseded"] += 1

        target = entity_uri.get(row["lei"])
        if target is None:
            stats["signal_about_dangling"] += 1
        else:
            triples.append(triple(node, P_SIGNAL_ABOUT, target))
            stats["signal_about_asserted"] += 1

        if row["supersedes"]:
            older = signal_uri(row["supersedes"])
            triples.append(triple(older, P_SUPERSEDED_BY, node))
            stats["supersession_edges"] += 1

    # --- coveredBy: EVERY coverage_assignment row, primacy separate --------
    # Fix round 1, Finding 1: all 150 rows, not just the 50 primaries -- this
    # product is anchored on the BANKER, and a primary-only load left 24 of
    # 37 bankers with an empty candidate set.
    distinct_bankers: set[str] = set()
    for row in coverage:
        prospect_node = entity_uri.get(row["lei"])
        if prospect_node is None:
            stats["covered_by_dangling"] += 1
            continue
        banker_node = banker_uri(row["banker_id"])
        triples.append(triple(prospect_node, P_COVERED_BY, banker_node))
        stats["covered_by_asserted"] += 1
        distinct_bankers.add(row["banker_id"])
        if row["is_primary"]:
            triples.append(triple(prospect_node, P_PRIMARY_BANKER_ID,
                                  row["banker_id"], literal=True))
            stats["primary_banker_id_asserted"] += 1
    stats["distinct_bankers_covered"] = len(distinct_bankers)

    # --- comparableTo: shared SIC, size band DISCLOSED not filtered --------
    # Fix round 1, Finding 2 + 3. Grouped by SIC alone; every DIRECTED pair
    # within a group gets its own comparableTo edge and its own
    # comparabilityBasis literal, asserted together in the same iteration so
    # the two counts can never diverge. The peer's LEI is embedded in the
    # basis text so two different peers of the same subject can never
    # produce an identical literal (which would silently collapse to one
    # triple under RDF set semantics and break the 1:1 count).
    groups = comparable_groups(prospects)
    band_by_lei = {p["lei"]: p["size_band"] for p in prospects}
    seen_prospects: set[str] = set()
    for sic, members in sorted(groups.items()):
        for i, a in enumerate(members):
            a_node = entity_uri.get(a["lei"])
            if a_node is None:
                continue
            for j, b in enumerate(members):
                if i == j:
                    continue
                b_node = entity_uri.get(b["lei"])
                if b_node is None:
                    continue
                basis = (f"shared SIC {sic}; size bands "
                        f"{band_by_lei[a['lei']]} vs {band_by_lei[b['lei']]} "
                        f"(peer {b['lei']})")
                triples.append(triple(a_node, P_COMPARABLE_TO, b_node))
                triples.append(triple(a_node, P_COMPARABILITY_BASIS, basis,
                                      literal=True))
                stats["comparable_edges"] += 1
                stats["comparability_basis_asserted"] += 1
                seen_prospects.add(a["lei"])
                seen_prospects.add(b["lei"])
    stats["comparable_pairs"] = stats["comparable_edges"] // 2
    stats["comparable_prospects"] = len(seen_prospects)
    stats["comparable_groups"] = {f"SIC {sic}": [p["lei"] for p in members]
                                  for sic, members in sorted(groups.items())}

    return triples, stats


# ===========================================================================
# Idempotency -- retract-then-assert, scoped by subject IRI (Rule 5)
# ===========================================================================

def _asserted_triples(predicate: str) -> list[tuple[str, str, bool]]:
    """(subject, object, is_literal) for every currently-asserted triple on
    `predicate`, anywhere in the ledger -- filtered to OUR subjects by the
    caller, never trusted as ours just because the predicate matches."""
    from ccf.config import FLUREE_LEDGER_V2
    q = f"SELECT ?s ?o FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s <{predicate}> ?o }}"
    out: list[tuple[str, str, bool]] = []
    for b in fluree.query(q).get("results", {}).get("bindings", []):
        out.append((b["s"]["value"], b["o"]["value"],
                    b["o"].get("type") == "literal"))
    return out


def _scoped_asserted(predicates: list[str],
                     subjects: set[str]) -> list[tuple[str, str, str, bool]]:
    """(predicate, subject, object, is_literal) across `predicates`, filtered
    to subjects in `subjects`."""
    out: list[tuple[str, str, str, bool]] = []
    for pred in predicates:
        for s, o, lit in _asserted_triples(pred):
            if s in subjects:
                out.append((pred, s, o, lit))
    return out


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def reconcile(*, dry_run: bool, signal_uris: set[str],
             prospect_uris: set[str]) -> int:
    """Retract every triple this loader owns, scoped by SUBJECT -- never a
    blind predicate-wide delete. Two populations (see module docstring):
    `SIGNAL_NODE_PREDICATES` for our own `OPPSIG-*` subjects (safe to
    retract in full), `PROSPECT_EDGE_PREDICATES` for the shared entity-node
    subjects (scoped to exactly these three predicate names, never touching
    another loader's triples on the same node)."""
    total = 0
    statements: list[str] = []
    by_pred: dict[str, int] = {}

    for pred, s, o, lit in (
        _scoped_asserted(SIGNAL_NODE_PREDICATES, signal_uris)
        + _scoped_asserted(PROSPECT_EDGE_PREDICATES, prospect_uris)
    ):
        by_pred[pred] = by_pred.get(pred, 0) + 1
        obj = f'"{_esc(o)}"' if lit else f"<{o}>"
        statements.append(f"<{s}> <{pred}> {obj} .")
        total += 1

    for pred, n in sorted(by_pred.items()):
        print(f"    {pred.rsplit('/', 1)[-1]:<20} {n:>6} asserted (ours)")

    if not statements:
        print("    nothing asserted -- nothing to retract")
        return 0
    print(f"    {total} triples to retract")
    if dry_run:
        print("    [dry-run] nothing retracted")
        return 0

    for i in range(0, len(statements), BATCH):
        fluree.update("DELETE DATA {\n" + "\n".join(statements[i:i + BATCH]) + "\n}")

    remaining = len(
        _scoped_asserted(SIGNAL_NODE_PREDICATES, signal_uris)
        + _scoped_asserted(PROSPECT_EDGE_PREDICATES, prospect_uris)
    )
    print(f"    retracted . triples remaining on our own subjects: {remaining}")
    if remaining:
        print("    WARNING -- retraction incomplete; not proceeding to the rebuild.")
    return remaining


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reconcile", action="store_true",
                    help="retract this loader's own triples before "
                         "rebuilding. Only needed when the artifact changed "
                         "a literal on an existing subject -- a plain "
                         "re-run against an unchanged artifact is already "
                         "idempotent because every subject and literal is "
                         "deterministic.")
    args = ap.parse_args()

    signals = load_signals()
    with pg_connect() as conn, conn.cursor() as cur:
        coverage = fetch_coverage_assignments(cur)
        prospects = fetch_prospects(cur)
    assign_size_bands(prospects)

    entity_uri = entity_uri_by_lei()
    n_types = len({s["signal_type"] for s in signals})
    print(f"  resolved {len(entity_uri)} entity nodes from the ledger")
    print(f"  {len(signals)} signals across {n_types} types . "
          f"{len(prospects)} covered prospects . "
          f"{len(coverage)} coverage_assignment rows")

    triples, stats = build(signals, coverage, prospects, entity_uri)

    signal_uris = {signal_uri(s["signal_id"]) for s in signals}
    prospect_uris = {entity_uri[p["lei"]] for p in prospects
                     if p["lei"] in entity_uri}

    print("\nWave 16 Task 12 -- Fluree load (Fix round 1)\n")
    print(f"  OpportunitySignal nodes   {stats['signals_typed']:>6}  "
          f"(current: {stats['current']}, superseded: {stats['superseded']})")
    print(f"  signalAbout asserted      {stats['signal_about_asserted']:>6}  "
          f"(dangling: {stats['signal_about_dangling']})")
    print(f"  supersededBy edges        {stats['supersession_edges']:>6}")
    print(f"  coveredBy asserted        {stats['covered_by_asserted']:>6}  "
          f"(dangling: {stats['covered_by_dangling']}, "
          f"distinct bankers: {stats['distinct_bankers_covered']})")
    print(f"  primaryBankerId asserted  {stats['primary_banker_id_asserted']:>6}")
    print(f"  comparableTo edges        {stats['comparable_edges']:>6}  "
          f"({stats['comparable_pairs']} pairs, "
          f"{stats['comparable_prospects']} prospects involved)")
    print(f"  comparabilityBasis        {stats['comparability_basis_asserted']:>6}  "
          f"(must equal comparableTo edges)")
    for group, leis in stats["comparable_groups"].items():
        print(f"      {group}: {leis}")
    print(f"  total triples             {len(triples):>6}")

    if args.reconcile:
        print("\n  --reconcile: retracting this loader's own triples "
              "(types, literals, edges) before rebuild")
        if reconcile(dry_run=args.dry_run, signal_uris=signal_uris,
                    prospect_uris=prospect_uris):
            return 1

    if args.dry_run:
        print("\n  [dry-run] nothing written to Fluree")
        return 0

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")
    print(f"\n  ledger now at t={fluree.ledger_t()} . "
          f"{fluree.count_triples():,} triples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
