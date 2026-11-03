#!/usr/bin/env python3
"""Wave 12 Task 9 — treasury edges into Fluree.

Design `docs/wave12-design.md` §4.1 splits the product cleanly: Postgres (Task
7, already loaded) owns every attribute — balances, notionals, yields, limits,
mandates. Fluree owns the graph: `heldAt` / `concentratedIn` (position ->
counterparty), typed `DepositAccount` / investment-position nodes, and the
regulatory posture overlay, time-versioned.

## Step 1 — the dormant Wave 10 hazard, re-verified independently

The coordinator reported this already checked before this loader was written;
verified again here rather than taken on faith, because "should not fire" is
exactly how Wave 11b's own hazard read the day before it did
(`known-issues.md` §10.5). `load_fluree_wave10.py`'s `OWNED_PREDICATES` is
**six** predicates, all confirmed by reading the file directly:

    isEmployedBy, isOfficerOf, isDirectorOf,
    coversClient, participatedIn, relatedToDeal

None of `heldAt`, `concentratedIn`, `observedIn`, `amends` — the four new
Wave 12 predicates named in the task-9 brief — appear in that set, by name or
by resolved IRI. `load_fluree_wave10.py --reconcile` cannot touch this
loader's writes.

## Reconcile scopes by SUBJECT, never by predicate — the non-negotiable rule

`known-issues.md` §10.5: Wave 11b turned `load_fluree_wave11a.py --reconcile`
into a silent data-loss hazard by asserting more edges on a predicate that
loader believed it owned outright — a belief true when written, false the
moment a second wave started writing the same predicate, and nothing raised
or logged the difference. `heldAt` and `concentratedIn` are new here and
unshared, but `supersededBy` (used by the posture overlay's one engineered
version chain) is NOT unshared — Waves 5, 11a and 11b already assert 215+
triples on it. So this loader follows `load_fluree_wave11b.py`'s established
shape exactly: `my_node_uris()` computes the exact, exhaustive set of subject
URIs this loader mints; `reconcile()` retracts only triples whose SUBJECT is
in that set, across every predicate this loader ever writes on an instance
node (`MY_PREDICATES`) — never a blind predicate-wide scan. That is what
keeps `supersededBy` safe in both directions.

## Two node populations already exist; this loader extends both, in place

`load_collateral_wave9.py` already created 20 `DepositAccount` nodes (`DEP-*`)
from a static JSON artifact — it never re-reads Postgres, so it will never see
Task 5/7's ~100 new `W12-*` rows. This loader is what gives those 100 rows a
Fluree identity: typed `DepositAccount` (the SAME bound class Wave 9 uses,
reused not redeclared — its T-box is already an `owl:Class` node in the
ledger), with the same `setOffAgainst` / conditional `nettedUnder` edge to
their holder that Wave 9 asserts for its own 20, so a query over ALL deposit
accounts does not silently see only 20 of 120. `DEP-*` and `W12-*` never
collide, so this is additive, not a rewrite of Wave 9's rows — confirmed live
before writing (`DEP-0001`..`DEP-0020` vs `W12-0001`..`W12-0100`, disjoint by
construction) and `load_collateral_wave9.py` has no `--reconcile` at all
(checked: no `DELETE`, no `TRUNCATE`, upsert-only), so there is nothing on
that side to collide with either.

## New FIBO terms — the design's own "no new binding" claim did not survive
## contact with "each position typed for both its instrument class and the
## roles it must answer"

`docs/wave12-design.md` §1.1 measured the terms *named in the spec's prose*
as already bound and concluded no new binding was needed. It never worked out
the concrete per-instrument-kind typing the task-9 brief's own constraint
demands, and that is a different, narrower question with a different answer.
Checked live against a shallow `edmcouncil/fibo` clone (git, no auth, 2026-08-2x)
rather than guessed from module names — the standing rule that module
membership does not pin an IRI:

    money-market-fund -> checked "MoneyMarketFund": ZERO hits anywhere in the
        clone. Closest genuine class: `fibo-sec-fund-fund:MutualFund`
        (SEC/Funds/Funds) — a money market fund legally IS a type of
        open-end/mutual fund; FIBO simply has no MMF-specific subclass.
    commercial-paper -> `fibo-sec-dbt-tstd:CommercialPaper`
        (SEC/Debt/TradedShortTermDebt) — EXACT match, subclass of
        `MoneyMarketInstrument`.
    treasury-bill -> `fibo-sec-dbt-bnd:TreasuryBill` (SEC/Debt/Bonds) — EXACT
        match, subclass of both `USTreasurySecurity` and `MoneyMarketInstrument`.

`fibo-fbc-pas-caa:InvestmentAccount` — the generic "role" type every position
also carries — needed NO new binding: it is already in the table, explicitly
tagged "(collateral-and-setoff, treasury-liquidity)" since Wave 8, and this is
simply its first use.

**These three (CommercialPaper, TreasuryBill, MutualFund) are new to
`docs/ccf_dataprep_v2.md` and the vault mirror is now stale on them** — see
the "Wave 12 addition" subsection added there, and the response to the
coordinator: the mirror refresh is flagged, and the corrected mirror is sent
through the agent exchange (`~/.agent-exchange/ccf-dataprep/outbox/`) per
CLAUDE.md, not edited in the vault directly.

`fibo-fnd-agr-ctr:Counterparty` was ALSO found live (real, exact match for the
spec's schema-row "Counterparty" entity) but is deliberately NOT asserted
here: the task-9 brief's typing constraint names only `DepositAccount` and
"each position", not the counterparty entity nodes, and those entity nodes
belong to Wave 3/6, not this loader — typing them here would mutate a subject
outside `my_node_uris()`, making the assertion permanently un-reconcilable by
anything. Left as a recorded, available term for whichever future task
actually needs it, not spent here on speculation.

## The regulatory posture overlay — synthetic, internal, time-versioned

No Postgres table backs this (checked: none of Task 5/7's DDL declares one),
and the spec's own catalog places it deliberately in Fluree — `docs/wave12-design.md`
§4.1's store table: "Regulatory posture overlay by jurisdiction | internal |
synthetic — internal | **Fluree** | P, T" — Fluree is the CCF store table's
named owner of `P` (policy binding), so this is the one element in this
loader that legitimately carries attribute values on its own node rather than
resolving them from Postgres.

Keyed by the 12 *actually-observed* `(jurisdiction, intent)` pairs — computed
by joining `deposit_account.jurisdiction` to `treasury_client.intent` via
`holder_lei`, not a full 8x3 cross product that would mint nodes for
combinations nothing in the data touches. One pair, `(US-NY,
reserve-buffer)`, carries TWO versions — `standard` tightened to
`enhanced-scrutiny` — chained with the SAME `ex:supersededBy` Wave 5
established, so `as_of` genuinely flips across the boundary date rather than
merely being labelled as if it does. The other 11 carry one open-ended
version each. `ex:PolicyVersion`'s T-box (Wave 5) is reused as a second type
on every posture node — not redeclared, exactly Wave 11b's precedent for
reusing `ex:IssuanceEvent` — because a regulatory posture genuinely IS a
policy version, and a future "give me every policy version in the ledger"
query should see it without needing to know this product's specific vocabulary.

    uv run loaders/load_fluree_wave12_treasury.py --dry-run
    uv run loaders/load_fluree_wave12_treasury.py
    uv run loaders/load_fluree_wave12_treasury.py --reconcile --dry-run
"""

from __future__ import annotations

import argparse
import sys

from ccf import fluree
from ccf.config import EX, EX_EXTENSION_SCHEMA_NOTE, PG_SCHEMA_V2, pg_connect
from loaders.load_collateral_wave9 import entity_uri_by_lei, esc, triple, uri

FIBO = "https://spec.edmcouncil.org/fibo/ontology/"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"

# --- Real FIBO binding, reused, NOT redeclared — Wave 9 already asserts its
#     T-box (`owl:Class` + label) in the ledger. -----------------------------
C_DEPOSIT = f"{FIBO}FBC/ProductsAndServices/ClientsAndAccounts/DepositAccount"

# --- Real FIBO binding, already in docs/ccf_dataprep_v2.md since Wave 8,
#     first MATERIALIZED (asserted as an owl:Class node) by this loader. ----
C_INVESTMENT_ACCOUNT = f"{FIBO}FBC/ProductsAndServices/ClientsAndAccounts/InvestmentAccount"

# --- Real FIBO bindings NEW to the binding table — verified live against the
#     edmcouncil/fibo clone; see module docstring and
#     docs/ccf_dataprep_v2.md "Wave 12 addition". -----------------------------
C_COMMERCIAL_PAPER = f"{FIBO}SEC/Debt/TradedShortTermDebt/CommercialPaper"
C_TREASURY_BILL = f"{FIBO}SEC/Debt/Bonds/TreasuryBill"
#: FIBO has NO `MoneyMarketFund` class (checked, zero hits) — `MutualFund` is
#: the closest genuine match for a money-market-fund position.
C_MUTUAL_FUND = f"{FIBO}SEC/Funds/Funds/MutualFund"

INSTRUMENT_CLASS = {
    "money-market-fund": C_MUTUAL_FUND,
    "commercial-paper": C_COMMERCIAL_PAPER,
    "treasury-bill": C_TREASURY_BILL,
}

# --- ex: extension — no FIBO class for a bank's internal jurisdiction/intent
#     regulatory-posture classification (checked: no RegulatoryPosture,
#     RegulatoryClassification, RegulatoryRegime, or similar anywhere in the
#     clone). -------------------------------------------------------------
C_REGULATORY_POSTURE = f"{EX}RegulatoryPosture"
#: Reused, NOT redeclared — Wave 5 already asserts this class's T-box.
C_POLICY_VERSION = f"{EX}PolicyVersion"

P_HELD_AT = f"{EX}heldAt"
P_CONCENTRATED_IN = f"{EX}concentratedIn"
#: Shared with Waves 5, 11a, 11b (215+ assertions already). Subject-scoped
#: retraction only — see reconcile()'s docstring.
P_SUPERSEDED_BY = f"{EX}supersededBy"
#: Shared with Wave 9 (20 assertions on its own DEP-* subjects). This loader
#: only ever writes these on W12-* subjects, so the two never collide even
#: though Wave 9 has no reconcile of its own to protect.
P_SETOFF_AGAINST = f"{EX}setOffAgainst"
P_NETTED_UNDER = f"{EX}nettedUnder"

BATCH = 400

# --- the posture overlay's one engineered supersession, so `as_of` actually
#     flips rather than merely being labelled time-versioned. ---------------
POSTURE_CHANGED = ("US-NY", "reserve-buffer")
POSTURE_EPOCH = "2024-01-02"           # matches benchmark_curve's own start
POSTURE_CHANGE_DATE = "2026-06-16"     # v2 effective from here
POSTURE_PRIOR_VALID_TO = "2026-06-15"  # v1's last valid day
POSTURE_OLD_LEVEL = "standard"
POSTURE_NEW_LEVEL = "enhanced-scrutiny"

#: Deterministic, synthetic — internal classification for the 11 unchanged
#: pairs. Not sourced from any real regulation — this element has no public
#: analogue (design §C: "Regulatory posture overlay by jurisdiction |
#: internal | synthetic — internal").
CORE_JURISDICTIONS = {"US-DE", "US-MD", "US-NY", "GB", "DE", "FR"}


def posture_level(jurisdiction: str) -> str:
    return "standard" if jurisdiction in CORE_JURISDICTIONS else "enhanced-scrutiny"


def posture_node(jurisdiction: str, intent: str, version: int) -> str:
    return uri(f"posture-{jurisdiction}-{intent}-v{version}")


def my_node_uris(position_ids: set[str], w12_account_ids: set[str],
                  posture_node_uris: set[str]) -> set[str]:
    """The full, exact set of node URIs this loader mints — investment
    position nodes, the new W12-* deposit account nodes, and every posture
    node. Nothing else in the estate constructs a `POS-*`, `W12-*` or
    `posture-*` local id (checked: `DEP-*` is Wave 9's own, disjoint prefix),
    so subject-membership in this set is an exact, safe reconcile scope."""
    uris = {uri(pid) for pid in position_ids}
    uris |= {uri(aid) for aid in w12_account_ids}
    uris |= set(posture_node_uris)
    return uris


#: Every predicate this loader ever asserts ON ONE OF ITS OWN instance
#: nodes — types, labels, literals, and edges alike. `reconcile()` scopes
#: retraction by SUBJECT against `my_node_uris()`, never by a blind scan of
#: these predicates — `supersededBy` and `setOffAgainst`/`nettedUnder` are
#: shared with other loaders' own subjects and a predicate-wide scan would
#: delete their triples too.
MY_PREDICATES = [
    RDF_TYPE, RDFS_LABEL,
    f"{EX}provenance", f"{EX}postureJurisdiction", f"{EX}postureIntent", f"{EX}postureLevel",
    f"{EX}validFrom", f"{EX}validTo",
    P_HELD_AT, P_CONCENTRATED_IN, P_SUPERSEDED_BY,
    P_SETOFF_AGAINST, P_NETTED_UNDER,
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
    URIs (`my_node_uris()`) — across every predicate it writes on an
    instance node, never a blind scan of a predicate.

    This is the non-negotiable rule the task-9 brief names explicitly and
    `known-issues.md` §10.5 records the failure mode for: scoping by
    predicate is only safe as long as this loader is the predicate's ONLY
    writer, and that belief decays silently the moment a second wave starts
    writing the same predicate — which is exactly what already happened to
    `supersededBy` (Waves 5, 11a, 11b) and `setOffAgainst`/`nettedUnder`
    (Wave 9). Scoping by subject instead is provably exact rather than
    merely convenient: every URI in `node_uris` is built from a `POS-*`,
    `W12-*` or `posture-*` local id, and nothing else in the estate mints
    any of those three prefixes (checked by grep across every loader before
    relying on this)."""
    total = 0
    statements: list[str] = []
    by_pred: dict[str, int] = {}
    for pred, s, o, lit in _my_asserted(node_uris):
        by_pred[pred] = by_pred.get(pred, 0) + 1
        obj = f'"{esc(o)}"' if lit else f"<{o}>"
        statements.append(f"<{s}> <{pred}> {obj} .")
        total += 1

    for pred, n in sorted(by_pred.items()):
        print(f"    {pred.rsplit('/', 1)[-1]:<16} {n:>5} asserted (ours)")

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


def build(clients: list[tuple[str, str]], positions: list[tuple],
          w12_accounts: list[tuple], combos: list[tuple[str, str]],
          entity_uri: dict[str, str]) -> tuple[list[str], dict]:
    """Compute every triple this loader will assert, deterministically."""
    triples: list[str] = []
    stats = {
        "position_dangling": 0, "account_dangling": 0,
        "positions_loaded": 0, "accounts_loaded": 0,
        "posture_nodes": 0, "posture_supersessions": 0,
    }

    # --- T-box: classes first used by this loader --------------------------
    for cls, note in (
        (C_INVESTMENT_ACCOUNT,
         "InvestmentAccount (real FIBO term, bound Wave 8 for "
         "treasury-liquidity; first materialized here)"),
        (C_COMMERCIAL_PAPER,
         "CommercialPaper (real FIBO term, SEC/Debt/TradedShortTermDebt — "
         "newly bound, Wave 12)"),
        (C_TREASURY_BILL,
         "TreasuryBill (real FIBO term, SEC/Debt/Bonds — newly bound, Wave 12)"),
        (C_MUTUAL_FUND,
         "MutualFund (real FIBO term, SEC/Funds/Funds — newly bound, Wave 12; "
         "FIBO has no MoneyMarketFund class, checked; closest genuine match "
         "for a money-market-fund position)"),
    ):
        triples.append(triple(cls, RDF_TYPE, OWL_CLASS))
        triples.append(triple(cls, RDFS_LABEL, note, literal=True))
    triples.append(triple(C_REGULATORY_POSTURE, RDF_TYPE, OWL_CLASS))
    triples.append(triple(C_REGULATORY_POSTURE, RDFS_LABEL,
                           "RegulatoryPosture", literal=True))
    triples.append(triple(C_REGULATORY_POSTURE, f"{EX}schemaNote",
                           EX_EXTENSION_SCHEMA_NOTE, literal=True))

    # --- investment positions: typed for instrument class AND role ---------
    for (position_id, holder_lei, counterparty_lei, instrument_kind,
         provenance) in positions:
        node = uri(position_id)
        instr_cls = INSTRUMENT_CLASS[instrument_kind]
        triples += [
            triple(node, RDF_TYPE, C_INVESTMENT_ACCOUNT),
            triple(node, RDF_TYPE, instr_cls),
            triple(node, RDFS_LABEL,
                   f"{instrument_kind} position {position_id}", literal=True),
            triple(node, f"{EX}provenance", provenance, literal=True),
        ]
        target = entity_uri.get(counterparty_lei)
        if target is None:
            stats["position_dangling"] += 1
        else:
            triples.append(triple(node, P_HELD_AT, target))
            triples.append(triple(node, P_CONCENTRATED_IN, target))
            stats["positions_loaded"] += 1

    # --- new W12-* deposit accounts: DepositAccount, extending Wave 9's 20 -
    for (account_id, holder_lei, jurisdiction, setoff_contractual,
         setoff_enforceable, provenance, currency) in w12_accounts:
        node = uri(account_id)
        triples += [
            triple(node, RDF_TYPE, C_DEPOSIT),
            triple(node, RDFS_LABEL,
                   f"{currency} deposit {account_id}", literal=True),
            triple(node, f"{EX}provenance", provenance, literal=True),
        ]
        holder = entity_uri.get(holder_lei)
        if holder is None:
            stats["account_dangling"] += 1
        else:
            triples.append(triple(node, P_SETOFF_AGAINST, holder))
            if setoff_enforceable:
                triples.append(triple(node, P_NETTED_UNDER, holder))
            stats["accounts_loaded"] += 1

    # --- regulatory posture overlay, time-versioned -------------------------
    posture_node_uris: set[str] = set()
    for jurisdiction, intent in combos:
        if (jurisdiction, intent) == POSTURE_CHANGED:
            v1 = posture_node(jurisdiction, intent, 1)
            v2 = posture_node(jurisdiction, intent, 2)
            posture_node_uris |= {v1, v2}
            for node, version, level, valid_from, valid_to in (
                (v1, 1, POSTURE_OLD_LEVEL, POSTURE_EPOCH, POSTURE_PRIOR_VALID_TO),
                (v2, 2, POSTURE_NEW_LEVEL, POSTURE_CHANGE_DATE, None),
            ):
                triples += [
                    triple(node, RDF_TYPE, C_REGULATORY_POSTURE),
                    triple(node, RDF_TYPE, C_POLICY_VERSION),
                    triple(node, RDFS_LABEL,
                           f"Regulatory posture — {jurisdiction} / {intent} "
                           f"(v{version}): {level}", literal=True),
                    triple(node, f"{EX}postureJurisdiction", jurisdiction, literal=True),
                    triple(node, f"{EX}postureIntent", intent, literal=True),
                    triple(node, f"{EX}postureLevel", level, literal=True),
                    triple(node, f"{EX}validFrom", valid_from, literal=True),
                    triple(node, f"{EX}provenance", "synthetic — internal",
                           literal=True),
                ]
                if valid_to:
                    triples.append(triple(node, f"{EX}validTo", valid_to,
                                           literal=True))
                stats["posture_nodes"] += 1
            triples.append(triple(v1, P_SUPERSEDED_BY, v2))
            stats["posture_supersessions"] += 1
        else:
            node = posture_node(jurisdiction, intent, 1)
            posture_node_uris.add(node)
            level = posture_level(jurisdiction)
            triples += [
                triple(node, RDF_TYPE, C_REGULATORY_POSTURE),
                triple(node, RDF_TYPE, C_POLICY_VERSION),
                triple(node, RDFS_LABEL,
                       f"Regulatory posture — {jurisdiction} / {intent} "
                       f"(v1): {level}", literal=True),
                triple(node, f"{EX}postureJurisdiction", jurisdiction, literal=True),
                triple(node, f"{EX}postureIntent", intent, literal=True),
                triple(node, f"{EX}postureLevel", level, literal=True),
                triple(node, f"{EX}validFrom", POSTURE_EPOCH, literal=True),
                triple(node, f"{EX}provenance", "synthetic — internal",
                       literal=True),
            ]
            stats["posture_nodes"] += 1

    stats["posture_node_uris"] = posture_node_uris
    return triples, stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reconcile", action="store_true",
                    help="retract this loader's own triples before "
                         "rebuilding. Required only if a regenerated "
                         "artifact changed a literal on an existing subject "
                         "— a plain re-run against unchanged Postgres rows "
                         "is already idempotent because every node URI is "
                         "deterministic.")
    args = ap.parse_args()

    S = PG_SCHEMA_V2
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, intent FROM "{S}".treasury_client ORDER BY lei')
        clients = cur.fetchall()

        cur.execute(f'''SELECT position_id, holder_lei, counterparty_lei,
                                instrument_kind, provenance
                           FROM "{S}".investment_position ORDER BY position_id''')
        positions = cur.fetchall()

        cur.execute(f'''SELECT account_id, holder_lei, jurisdiction,
                                setoff_contractual, setoff_enforceable,
                                provenance, currency
                           FROM "{S}".deposit_account
                          WHERE account_id LIKE 'W12-%%'
                          ORDER BY account_id''')
        w12_accounts = cur.fetchall()

        cur.execute(f'''SELECT DISTINCT d.jurisdiction, t.intent
                           FROM "{S}".deposit_account d
                           JOIN "{S}".treasury_client t ON t.lei = d.holder_lei
                          ORDER BY 1, 2''')
        combos = cur.fetchall()

    entity_uri = entity_uri_by_lei()
    print(f"  resolved {len(entity_uri)} entity nodes from the ledger")
    print(f"  {len(clients)} treasury clients · {len(positions)} positions · "
          f"{len(w12_accounts)} new W12-* deposit accounts · "
          f"{len(combos)} (jurisdiction, intent) combos")

    triples, stats = build(clients, positions, w12_accounts, combos, entity_uri)
    posture_node_uris = stats.pop("posture_node_uris")

    position_ids = {p[0] for p in positions}
    w12_account_ids = {a[0] for a in w12_accounts}
    node_uris = my_node_uris(position_ids, w12_account_ids, posture_node_uris)

    print("\nWave 12 Task 9 — Fluree load\n")
    print(f"  investment positions   {stats['positions_loaded']:>6}  "
          f"(dangling: {stats['position_dangling']})")
    print(f"  new deposit accounts   {stats['accounts_loaded']:>6}  "
          f"(dangling: {stats['account_dangling']})")
    print(f"  posture nodes          {stats['posture_nodes']:>6}  "
          f"across {len(combos)} combos "
          f"(supersessions: {stats['posture_supersessions']})")
    print(f"  total triples          {len(triples):>6}")
    print(f"  engineered posture change: {POSTURE_CHANGED} "
          f"{POSTURE_OLD_LEVEL} -> {POSTURE_NEW_LEVEL} on {POSTURE_CHANGE_DATE}")

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
