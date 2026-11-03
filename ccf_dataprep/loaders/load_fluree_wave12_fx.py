#!/usr/bin/env python3
"""Wave 12 Task 14 — FX reconciliation edges into Fluree.

`load_postgres_wave12_fx.py` (already loaded) owns every attribute that has
a "current value" — the trade terms, per-system rates, tick series, break
variances. This loader owns the graph: `observedIn` (trade -> per-system
observation), `amends` (the amendment chain per trade), per-system
observation timestamps and clock offsets, and the timing-artefact break
assertions — exactly the four groups `task-14-brief.md` names.

## Fix round 1 — RULING F23: `ex:observedAt` renamed to `ex:systemObservedAt`

The observation timestamp belongs in Fluree (the spec's §C: "system
observation timestamps and clock offsets" -> Fluree, "internal trade records
per system" -> Postgres) — that part of the original design was correct, and
`system_trade_record.observed_at` was dropped from Postgres rather than the
Fluree literal being removed. What was wrong was the PREDICATE NAME:
`ex:observedAt` is already claimed by Wave 11b as a Postgres-owned
surveillance-signal attribute (`validators/partition.py`'s
`POSTGRES_OWNED_ATTRS`), so asserting it here made the partition validator
report a real cross-wave predicate collision as a single-writer leak. Same
shape Task 9 already hit and fixed once, for `jurisdiction`/`intent` ->
`postureJurisdiction`/`postureIntent`: **a predicate name is estate-wide**,
not scoped to whichever loader is currently writing it. Renamed to
`ex:systemObservedAt`. Because Fluree is append-only, the 1,815 triples
fix round 0 asserted under the old name are cleaned up by a real
`--reconcile` (the old predicate stays in `MY_PREDICATES` under
`P_OBSERVED_AT_LEGACY` for exactly this one migration) rather than by any
direct mutation.

## Break assertions carry NO value at all — stricter than RULING F22 requires

RULING F22 is written against `break_record`, the Postgres table: seven
named columns, `designed_class` the one deliberate answer-key exception,
`gap_s` / `true_a` / `true_b` / `aligned_a` / `aligned_b` /
`aligned_diff_pips` / `timing_component_pips` never loaded. That rule is
scoped to one table, but the reasoning behind it — a consumer must not be
able to classify a break by reading one stored field, sidestepping the
clock alignment this product exists to demonstrate — applies with equal
force to any store. So this loader's break nodes carry **structure only**:
which trade, which two systems disagreed. No `raw_variance`, no
`designed_class`, nothing numeric. A consumer who wants the (deliberately
gated) answer key has exactly one place to look — Postgres `break_record`,
where it is named and documented as such — and cannot get it by a graph
traversal instead. This is not merely compliant with F22's letter; it makes
the discriminator-leak defect structurally impossible on the Fluree side.

## `amends` is REUSED, not redeclared — and is a SHARED predicate

`load_temporal_wave5.py` already asserts 25 `ex:amends` edges, from
facility-amendment event nodes to the facility they amend. This loader adds
edges of its own, from FX amendment-event nodes to what THEY amend (the
trade, or the prior amendment in the same trade's chain) — same predicate,
disjoint subject population (`amd-TRD-W12-*` here vs `AMD-*` there).
`known-issues.md` §10.5: a predicate believed "ours alone" decays silently
the moment a second wave writes it, and the failure it causes is a
retraction that deletes someone else's edges with nothing raised. So
`reconcile()` here follows the same rule Wave 5's sibling loaders already
settled on: scope retraction to **subject membership** in the exact set of
node URIs this loader mints (`my_node_uris()`), never a blind scan of
`amends` or any other predicate.

## What is deliberately NOT asserted here

No edge from a trade node to its counterparty entity. `task-14-brief.md`'s
Fluree assertion list is exactly `observedIn`, `amends`, timestamps/offsets,
and break assertions — four things, not five. The counterparty is already
resolvable through Postgres (`fx_trade.counterparty_lei`) and adding a
graph edge nobody asked for is exactly the "spent on speculation" pattern
`load_fluree_wave12_treasury.py` deliberately avoided for `Counterparty`.
Left available for whichever future task actually needs it.

## New node populations, all disjoint from every existing prefix (checked)

    ex:TRD-W12-####            trade nodes (mints TRD- here for the first
                                time — grepped, no other loader uses it)
    ex:sys-{trading,settlement,risk}   3 system nodes, static
    ex:obs-{trade_id}-{system}-{seq}   per-system observation nodes
    ex:amd-{trade_id}-{seq}            amendment-event nodes
    ex:BRK-...                         break nodes (break_id is already
                                        globally unique and BRK-prefixed)

## FIBO typing — two real terms materialized here for the first time

`Trade` and `TradeLifecycleEvent` (`fibo-fbc-pas-fpas:...`) are both already
in `docs/ccf_dataprep_v2.md`'s binding table (bound Wave 8, per
`docs/wave12-design.md` §1.1) but had never been asserted as `owl:Class`
nodes in the ledger before this loader — same "bound in the table, first
materialized by the loader that finally needs it" shape as
`InvestmentAccount` in Task 9. `SystemObservation`, `ReconciliationBreak`,
and `TradeSystem` have no FIBO equivalent (FIBO models the trade and its
lifecycle events, not one internal system's booking snapshot, a detected
cross-system discrepancy, or a bank's own system inventory) and are declared
as `ex:` extensions with `isFiboTerm false` and the standard schema note —
no vault mirror refresh needed, because none of these three is a claim about
a FIBO term.

    uv run loaders/load_fluree_wave12_fx.py --dry-run
    uv run loaders/load_fluree_wave12_fx.py
    uv run loaders/load_fluree_wave12_fx.py --reconcile --dry-run
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from ccf import fluree
from ccf.config import EX, EX_EXTENSION_SCHEMA_NOTE, PG_SCHEMA_V2, pg_connect
from ccf.currency import verify_current
from loaders.load_collateral_wave9 import esc, triple, uri

FIBO = "https://spec.edmcouncil.org/fibo/ontology/"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"

# --- Real FIBO bindings, already in docs/ccf_dataprep_v2.md since Wave 8,
#     first MATERIALIZED (asserted as owl:Class nodes) by this loader. -------
C_TRADE = f"{FIBO}FBC/ProductsAndServices/FinancialProductsAndServices/Trade"
C_TRADE_LIFECYCLE_EVENT = (
    f"{FIBO}FBC/ProductsAndServices/FinancialProductsAndServices/"
    "TradeLifecycleEvent"
)

# --- ex: extensions — no FIBO equivalent (see module docstring). -----------
C_SYSTEM_OBSERVATION = f"{EX}SystemObservation"
C_RECONCILIATION_BREAK = f"{EX}ReconciliationBreak"
C_TRADE_SYSTEM = f"{EX}TradeSystem"

P_OBSERVED_IN = f"{EX}observedIn"
#: Shared with Wave 5 (25 assertions on `AMD-*` facility-amendment subjects).
#: Subject-scoped retraction only — see reconcile()'s docstring.
P_AMENDS = f"{EX}amends"
P_RECORDED_BY_SYSTEM = f"{EX}recordedBySystem"
P_INVOLVES_TRADE = f"{EX}involvesTrade"
P_INVOLVES_SYSTEM_A = f"{EX}involvesSystemA"
P_INVOLVES_SYSTEM_B = f"{EX}involvesSystemB"
#: RULING F23 (fix round 1). `ex:observedAt` is already claimed by Wave 11b
#: as a Postgres-owned surveillance-signal attribute
#: (`validators/partition.py`'s `POSTGRES_OWNED_ATTRS`), so writing it here
#: made `partition.py` report a real cross-wave predicate COLLISION as a
#: single-writer LEAK. Renamed, same precedent as Task 9's
#: `ex:postureJurisdiction`/`ex:postureIntent` — a predicate name is
#: estate-wide, not scoped to the loader that happens to be reading it.
P_SYSTEM_OBSERVED_AT = f"{EX}systemObservedAt"
#: The pre-fix name. No longer written (see P_SYSTEM_OBSERVED_AT above), but
#: kept as its own constant and left in MY_PREDICATES so a real --reconcile
#: retracts the 1,815 stale triples fix round 0 asserted under this name
#: before rebuilding under the new one. Safe to delete once that migration
#: has run everywhere this loader is deployed.
P_OBSERVED_AT_LEGACY = f"{EX}observedAt"

BATCH = 400


def my_node_uris(trade_ids: set[str], system_names: set[str],
                  observation_ids: set[str], amendment_ids: set[str],
                  break_ids: set[str]) -> set[str]:
    """The full, exact set of node URIs this loader mints. Nothing else in
    the estate constructs a `TRD-`, `sys-`, `obs-`, `amd-`, or `BRK-` local
    id (checked by grep before relying on this), so subject-membership in
    this set is an exact, safe reconcile scope."""
    uris = {uri(tid) for tid in trade_ids}
    uris |= {uri(f"sys-{s}") for s in system_names}
    uris |= {uri(o) for o in observation_ids}
    uris |= {uri(a) for a in amendment_ids}
    uris |= {uri(b) for b in break_ids}
    return uris


#: Every predicate this loader ever asserts on one of its own subjects.
#: `reconcile()` scopes retraction by SUBJECT against `my_node_uris()`,
#: never by a blind scan of these predicates — `amends` is shared with
#: Wave 5's own (disjoint) subjects and a predicate-wide scan would delete
#: those edges too.
MY_PREDICATES = [
    RDF_TYPE, RDFS_LABEL, f"{EX}provenance", f"{EX}isFiboTerm",
    f"{EX}schemaNote",
    P_OBSERVED_IN, P_AMENDS, P_RECORDED_BY_SYSTEM,
    P_INVOLVES_TRADE, P_INVOLVES_SYSTEM_A, P_INVOLVES_SYSTEM_B,
    f"{EX}clockOffsetSeconds", P_SYSTEM_OBSERVED_AT, P_OBSERVED_AT_LEGACY,
    f"{EX}amendmentSeq", f"{EX}actionType", f"{EX}eventTimestamp",
]


def _asserted_triples(predicate: str) -> list[tuple[str, str, bool]]:
    """(subject, object, is_literal) for every currently-asserted triple on
    `predicate`, anywhere in the ledger — filtered to OUR subjects by the
    caller, never trusted as ours just because the predicate matches."""
    from ccf.config import FLUREE_LEDGER_V2
    q = f"SELECT ?s ?o FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s <{predicate}> ?o }}"
    out: list[tuple[str, str, bool]] = []
    for b in fluree.query(q).get("results", {}).get("bindings", []):
        out.append((b["s"]["value"], b["o"]["value"],
                    b["o"].get("type") == "literal"))
    return out


def _my_asserted(node_uris: set[str]) -> list[tuple[str, str, str, bool]]:
    """(predicate, subject, object, is_literal) across every predicate this
    loader writes, filtered to subjects in `node_uris`."""
    out: list[tuple[str, str, str, bool]] = []
    for pred in MY_PREDICATES:
        for s, o, lit in _asserted_triples(pred):
            if s in node_uris:
                out.append((pred, s, o, lit))
    return out


def reconcile(*, dry_run: bool, node_uris: set[str]) -> int:
    """Retract every triple whose SUBJECT is one of this loader's own node
    URIs — across every predicate it writes on an instance node, never a
    blind scan of a predicate.

    `known-issues.md` §10.5 records the failure mode: a loader that believed
    it was the sole author of a predicate turned `--reconcile` into a
    silent-deletion hazard the moment a second wave started writing the same
    predicate — which is exactly `amends`'s situation here (Wave 5 already
    asserts 25 edges on it, on its own `AMD-*` subjects). Scoping by subject
    instead is provably exact: every URI in `node_uris` is built from a
    `TRD-`, `sys-`, `obs-`, `amd-`, or `BRK-` local id, and nothing else in
    the estate mints any of those five prefixes."""
    total = 0
    statements: list[str] = []
    by_pred: dict[str, int] = {}
    for pred, s, o, lit in _my_asserted(node_uris):
        by_pred[pred] = by_pred.get(pred, 0) + 1
        obj = f'"{esc(o)}"' if lit else f"<{o}>"
        statements.append(f"<{s}> <{pred}> {obj} .")
        total += 1

    for pred, n in sorted(by_pred.items()):
        print(f"    {pred.rsplit('/', 1)[-1]:<20} {n:>5} asserted (ours)")

    if not statements:
        print("    nothing asserted — nothing to retract")
        return 0
    print(f"    {total} triples to retract")
    if dry_run:
        print("    [dry-run] nothing retracted")
        return 0

    for i in range(0, len(statements), BATCH):
        fluree.update("DELETE DATA {\n" + "\n".join(statements[i:i + BATCH]) + "\n}")

    remaining = len(_my_asserted(node_uris))
    print(f"    retracted · triples remaining on our own subjects: {remaining}")
    if remaining:
        print("    WARNING — retraction incomplete; not proceeding to the rebuild.")
    return remaining


def build(trades: list[dict], clock_offsets: list[dict],
          system_records: list[dict], amendments: list[dict],
          breaks: list[dict]) -> tuple[list[str], dict]:
    """Compute every triple this loader will assert, deterministically."""
    triples: list[str] = []
    stats = {"trades": 0, "systems": 0, "observations": 0,
              "amendments": 0, "breaks": 0, "dangling_breaks": 0}

    # --- T-box ---------------------------------------------------------
    for cls, note in (
        (C_TRADE, "Trade (real FIBO term, FBC/ProductsAndServices/"
                  "FinancialProductsAndServices — bound Wave 8; first "
                  "materialized here)"),
        (C_TRADE_LIFECYCLE_EVENT,
         "TradeLifecycleEvent (real FIBO term, same module — bound Wave 8; "
         "first materialized here; used for amendment events)"),
    ):
        triples.append(triple(cls, RDF_TYPE, OWL_CLASS))
        triples.append(triple(cls, RDFS_LABEL, note, literal=True))
    for cls, label in (
        (C_SYSTEM_OBSERVATION,
         "SystemObservation (ex: extension — no FIBO term for one internal "
         "system's booking snapshot of a trade)"),
        (C_RECONCILIATION_BREAK,
         "ReconciliationBreak (ex: extension — no FIBO term for a detected "
         "cross-system discrepancy)"),
        (C_TRADE_SYSTEM,
         "TradeSystem (ex: extension — no FIBO term for a bank's own "
         "internal booking/settlement/risk system)"),
    ):
        triples.append(triple(cls, RDF_TYPE, OWL_CLASS))
        triples.append(triple(cls, RDFS_LABEL, label, literal=True))
        triples.append(triple(cls, f"{EX}isFiboTerm", "false", literal=True))
        triples.append(triple(cls, f"{EX}schemaNote",
                               EX_EXTENSION_SCHEMA_NOTE, literal=True))

    # --- system nodes: 3, static, from clock_offsets ------------------------
    for co in clock_offsets:
        node = uri(f"sys-{co['system_name']}")
        triples += [
            triple(node, RDF_TYPE, C_TRADE_SYSTEM),
            triple(node, RDFS_LABEL, f"system: {co['system_name']}", literal=True),
            triple(node, f"{EX}clockOffsetSeconds", str(co["offset_s"]), literal=True),
            triple(node, f"{EX}provenance", co["provenance"], literal=True),
        ]
        stats["systems"] += 1

    # --- trade nodes ---------------------------------------------------
    for t in trades:
        node = uri(t["trade_id"])
        triples += [
            triple(node, RDF_TYPE, C_TRADE),
            triple(node, RDFS_LABEL, f"FX trade {t['trade_id']} ({t['pair']})",
                   literal=True),
            triple(node, f"{EX}provenance", t["provenance"], literal=True),
        ]
        stats["trades"] += 1

    # --- per-system observation nodes, observedIn from the trade -----------
    for r in system_records:
        obs_id = f"obs-{r['trade_id']}-{r['system_name']}-{r['amendment_seq']}"
        node = uri(obs_id)
        sys_node = uri(f"sys-{r['system_name']}")
        triples += [
            triple(node, RDF_TYPE, C_SYSTEM_OBSERVATION),
            triple(node, RDFS_LABEL,
                   f"{r['system_name']} observation of {r['trade_id']} "
                   f"(amendment {r['amendment_seq']})", literal=True),
            triple(node, f"{EX}amendmentSeq", str(r["amendment_seq"]), literal=True),
            triple(node, P_SYSTEM_OBSERVED_AT, r["observed_at"], literal=True),
            triple(node, f"{EX}provenance", r["provenance"], literal=True),
            triple(node, P_RECORDED_BY_SYSTEM, sys_node),
            triple(uri(r["trade_id"]), P_OBSERVED_IN, node),
        ]
        stats["observations"] += 1

    # --- amendment-event nodes, chained via amends --------------------------
    by_trade: dict[str, list[dict]] = defaultdict(list)
    for a in amendments:
        by_trade[a["trade_id"]].append(a)
    for trade_id, group in by_trade.items():
        group.sort(key=lambda a: a["amendment_seq"])
        prior_node = uri(trade_id)  # seq 1 amends the trade itself
        for a in group:
            node = uri(f"amd-{trade_id}-{a['amendment_seq']}")
            triples += [
                triple(node, RDF_TYPE, C_TRADE_LIFECYCLE_EVENT),
                triple(node, RDFS_LABEL,
                       f"Amendment {a['amendment_seq']} to {trade_id} "
                       f"({a['action_type']})", literal=True),
                triple(node, f"{EX}amendmentSeq", str(a["amendment_seq"]), literal=True),
                triple(node, f"{EX}actionType", a["action_type"], literal=True),
                triple(node, f"{EX}eventTimestamp", a["event_ts"], literal=True),
                triple(node, f"{EX}provenance", a["provenance"], literal=True),
                triple(node, P_AMENDS, prior_node),
            ]
            stats["amendments"] += 1
            prior_node = node  # next amendment in the chain amends THIS one

    # --- break nodes: structure only, no discriminating value (see module
    #     docstring) --------------------------------------------------------
    trade_ids = {t["trade_id"] for t in trades}
    system_uris = {co["system_name"]: uri(f"sys-{co['system_name']}")
                   for co in clock_offsets}
    for b in breaks:
        if b["trade_id"] not in trade_ids:
            stats["dangling_breaks"] += 1
            continue
        node = uri(b["break_id"])
        triples += [
            triple(node, RDF_TYPE, C_RECONCILIATION_BREAK),
            triple(node, RDFS_LABEL, f"break {b['break_id']}", literal=True),
            triple(node, f"{EX}provenance", b["provenance"], literal=True),
            triple(node, P_INVOLVES_TRADE, uri(b["trade_id"])),
            triple(node, P_INVOLVES_SYSTEM_A, system_uris[b["system_a"]]),
            triple(node, P_INVOLVES_SYSTEM_B, system_uris[b["system_b"]]),
        ]
        stats["breaks"] += 1

    return triples, stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reconcile", action="store_true",
                    help="retract this loader's own triples before "
                         "rebuilding. Required only if a regenerated "
                         "artifact changed a literal on an existing subject "
                         "— a plain re-run against unchanged inputs is "
                         "already idempotent because every node URI is "
                         "deterministic.")
    args = ap.parse_args()

    fx_doc, currency_note = verify_current("wave12_fx.json")
    print(f"  artifact currency: {currency_note}")

    trades = fx_doc["trades"]
    clock_offsets = fx_doc["clock_offsets"]
    system_records = fx_doc["system_records"]
    amendments = fx_doc["amendments"]
    breaks = fx_doc["breaks"]

    # Referential sanity: every fx_trade this loader will point at must
    # actually exist in the Postgres table load_postgres_wave12_fx.py wrote
    # — belt-and-suspenders against the two artifacts drifting apart.
    S = PG_SCHEMA_V2
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT trade_id FROM "{S}".fx_trade')
        pg_trade_ids = {row[0] for row in cur.fetchall()}
    missing_in_pg = {t["trade_id"] for t in trades} - pg_trade_ids
    if missing_in_pg:
        raise RuntimeError(
            f"{len(missing_in_pg)} trade(s) in wave12_fx.json are not in "
            f"Postgres ccf_v2.fx_trade — run load_postgres_wave12_fx.py "
            f"first: {sorted(missing_in_pg)[:5]}"
        )

    triples, stats = build(trades, clock_offsets, system_records,
                            amendments, breaks)

    trade_ids = {t["trade_id"] for t in trades}
    system_names = {co["system_name"] for co in clock_offsets}
    observation_ids = {
        f"obs-{r['trade_id']}-{r['system_name']}-{r['amendment_seq']}"
        for r in system_records
    }
    amendment_ids = {
        f"amd-{a['trade_id']}-{a['amendment_seq']}" for a in amendments
    }
    break_ids = {b["break_id"] for b in breaks}
    node_uris = my_node_uris(trade_ids, system_names, observation_ids,
                              amendment_ids, break_ids)

    print("\nWave 12 Task 14 — Fluree FX load\n")
    print(f"  trade nodes            {stats['trades']:>6}")
    print(f"  system nodes           {stats['systems']:>6}")
    print(f"  observation nodes      {stats['observations']:>6}  "
          f"(observedIn edges: {stats['observations']})")
    print(f"  amendment nodes        {stats['amendments']:>6}  "
          f"(amends edges: {stats['amendments']})")
    print(f"  break nodes            {stats['breaks']:>6}  "
          f"(dangling: {stats['dangling_breaks']})")
    print(f"  total triples          {len(triples):>6}")

    expected = {
        "trade nodes": (stats["trades"], 500),
        "observation nodes": (stats["observations"], 1_815),
        "amendment nodes": (stats["amendments"], 105),
        "break nodes": (stats["breaks"], 60),
    }
    mismatches = {k: v for k, v in expected.items() if v[0] != v[1]}
    if mismatches:
        raise RuntimeError(f"node-count mismatch vs. artifact expectation: "
                            f"{mismatches}")

    if args.reconcile:
        print("\n  --reconcile: retracting this loader's own triples "
              "(types, labels, literals, edges) before rebuild")
        if reconcile(dry_run=args.dry_run, node_uris=node_uris):
            return 1

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
