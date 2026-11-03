#!/usr/bin/env python3
"""Deal structure and dated trigger assertions into Fluree.

    uv run loaders/load_abs_fluree_wave14.py --dry-run
    uv run loaders/load_abs_fluree_wave14.py

## Why the thresholds live here and the measures do not

A threshold is a temporal fact: it holds from an effective date, and it can be
superseded. That is Fluree's slice (`T`). A delinquency percentage is a
measure computed from the pool, which is Postgres's slice (`E`). Putting the
measure here too would duplicate an attribute across stores -- the one thing
CLAUDE.md forbids outright -- and would let the two disagree silently.

Subordination is the mirror of that rule. `loaders/load_abs_structure_wave14.py`
deliberately drops `subordinate_to` from Postgres and keeps only
`seniority_rank`, because a rank is an attribute of one tranche and
subordination is an edge between two. This loader is the single writer of
that edge.

## Explicit typing, because Fluree does not reason

Fluree runs without OWL inference, so a node answers only the type queries it
was explicitly given. A deal is therefore typed BOTH
`fibo-sec-dbt-pbs:AssetBackedSecurity` and `fibo-sec-dbt-pbs:PoolBackedSecurity`
-- nothing derives the second from the first.

Tranche nodes carry `fibo-sec-dbt-pbs:Tranche` and nothing else, on purpose.
Fluree is append-only: a type asserted here can never be removed, only
contradicted. Adding speculative supertypes to cover a query nobody has
written yet is a permanent commitment made on a guess, so the type set is
kept to the one role Tasks 10-15 actually query against.

## `subordinate_to` is a LIST, and interpolating it would be unrecoverable

Task 6 made `subordinate_to` a list -- Toyota's Class A-3 is genuinely
subordinate to both A-2a and A-2b, which are siblings at the same rank. An
f-string over the list would write the list's *repr* into the URI:

    http://example.org/fibo/abs-tranche-['TAOT-2022-B-A-2a', 'TAOT-2022-B-A-2b']

Brackets, quotes, a comma and a space inside a URI, in an append-only store.
The list is iterated, one edge per element, and `_check_uri` refuses any URI
carrying a character that has no business in one.

## Composite thresholds: the headline number is not the threshold

Two triggers state a threshold as a SUM of components:

    "the sum of (i) 22.80% of the Pool Balance ... and (ii) 1.50% of ..."

`threshold_value` carries only the first percent. Writing that alone would
assert the OC target IS 22.80%, which is false -- it is 22.80% of one balance
plus 1.50% of another. Every element of `threshold_all_percents` is emitted
as an `ex:thresholdComponent`, alongside `ex:thresholdValue`, so a consumer
can see that the headline figure is partial. Single-component triggers are
unaffected: they get one component that equals the value.

## The two dates are the whole bitemporal mechanism -- never `now`

An original threshold was *in force* from the day the deal priced and
*knowable* from the day the prospectus was filed. For these deals both are
the 424B5 filing date, carried by `deals.json` as `prospectus_filed`.

Valid time is `ex:validFrom`, which is this estate's existing spelling for
"when the fact was true in the world" -- 1,724 assertions across Waves 5, 7,
11a and 11b. An earlier draft called it `ex:effectiveFrom`, a third name for
a concept that already has one. In a store that cannot retract, a second
spelling is not a synonym: it is a predicate half the estate's queries miss.

Stamping `assertedAt` with today's date would break Task 13 silently: today
is later than the amendment's own assertion date, so `threshold_known_as_of`
would find no assertion at or before the gap day and return `None`. The
divergence check would then pass -- `13.50 != None` -- green while measuring
nothing.

## Set semantics cover a re-run, not a CHANGED source value

Re-running this loader unchanged is a no-op: RDF is a set, so identical
triples dedupe. That says nothing about a *changed* one. A corrected
threshold in `prospectus_extract.json` would INSERT a second, different value
on the same subject and predicate, and with no upsert-by-subject-predicate
both would live forever with nothing marking which supersedes which.

So `ledger_conflicts` runs before any write and refuses when the ledger
already holds an object this run does not assert. It never resolves the
disagreement -- superseding is Task 10's modelled operation, and must be a
deliberate act rather than a side effect of re-running a loader.

## Every SPARQL statement carries an explicit FROM

Fluree returns HTTP 500, not a helpful 400, for a query with no dataset
specification. A verification query missing `FROM` fails AFTER a successful
load, which reads as a bad load and invites a "fix" to the loader.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, REPO_ROOT

REGISTRY = REPO_ROOT / "sources" / "absee" / "deals.json"
EXTRACT = REPO_ROOT / "sources" / "absee" / "prospectus_extract.json"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"

C_TRANCHE = f"{FIBO}SEC/Debt/PoolBackedSecurities/Tranche"
C_ABS = f"{FIBO}SEC/Debt/PoolBackedSecurities/AssetBackedSecurity"
C_POOL_BACKED = f"{FIBO}SEC/Debt/PoolBackedSecurities/PoolBackedSecurity"
C_TRIGGER_EVENT = f"{FIBO}SEC/Debt/CollateralizedDebtObligations/TriggerEvent"
C_SERVICER = f"{FIBO}LOAN/LoansGeneral/Loans/Servicer"

P_SPECIFIES_TRIGGER = f"{FIBO}SEC/Debt/CollateralizedDebtObligations/specifiesTrigger"
# RULING F53: `isSubordinatedTo` (SEC/Debt/DebtInstruments), NOT
# `isSubordinateTo` (FND/Agreements/Contracts). The latter was bound and used
# for 16 tranche->tranche edges, and it is the WRONG property: its domain and
# range are `WrittenContract` and it means "the primary contract referenced by
# a subordinate agreement" -- a document cross-reference, not a payment
# waterfall. This one has domain and range `TradableDebtInstrument` and is
# defined as "the target security has a higher priority than the security in
# question", which is exactly a tranche waterfall, in the same direction we
# already assert. Tranche is a TradableDebtInstrument by the FIBO chain
# (Tranche -> StructuredFinanceInstrument -> PoolBackedSecurity ->
# TradableDebtInstrument), so nothing is violated.
#
# The original was "verified against the EDM Council source" by fetching the
# term URL and seeing HTTP 200 -- which verifies NOTHING. Measured 2026-08-23:
#   .../SEC/Debt/PoolBackedSecurities/NotARealTermXYZ  ->  HTTP 200, 43,640 bytes
# The path prefix is content-negotiated and the local name is ignored entirely.
# The only valid test is grepping the containing ontology for
# rdf:about="&prefix;LocalName", which returns 0 for that bogus name and 1 for
# this one.
P_IS_SUBORDINATE_TO = f"{FIBO}SEC/Debt/DebtInstruments/isSubordinatedTo"
P_IS_COLLATERALIZATION_OF = f"{FIBO}FBC/DebtAndEquities/Debt/isCollateralizationOf"

# No FIBO term exists for these -- they are `ex:` deliberately, not by
# omission. `servicedBy` is on the do-not-bind list in
# docs/ccf_dataprep_v2.md; `validFrom`, `assertedAt` and `provenance` are
# already bound there. The four threshold/anchor predicates were bound in
# the same commit as this loader, before the write -- CLAUDE.md's
# definition of done requires binding upstream, and an append-only store
# makes that ordering load-bearing rather than procedural.
P_SERVICED_BY = f"{EX}servicedBy"
P_THRESHOLD_VALUE = f"{EX}thresholdValue"
P_THRESHOLD_COMPONENT = f"{EX}thresholdComponent"
P_THRESHOLD_UNIT = f"{EX}thresholdUnit"
P_VALID_FROM = f"{EX}validFrom"
P_ASSERTED_AT = f"{EX}assertedAt"
P_PROVENANCE = f"{EX}provenance"
P_ANCHOR = f"{EX}passageAnchor"

# Anything outside this set inside a URI means an identifier was built from a
# value that was not a plain string -- a list, a dict, a None. Append-only
# store: this must fail before the write, not be noticed after it.
_URI_FORBIDDEN = set(" \t\n\"'<>[]{}|\\^`,")


def esc(t: str) -> str:
    return t.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _check_uri(u: str) -> str:
    bad = sorted(_URI_FORBIDDEN & set(u))
    if bad:
        raise ValueError(f"refusing malformed URI {u!r}: contains {bad}")
    return u


class Stmt(NamedTuple):
    """One assertion, kept structured rather than as a rendered string.

    The pre-write conflict guard has to compare incoming objects against what
    the ledger already holds. Re-parsing N-Triples to do that would mean
    unescaping literals correctly on a path whose whole job is to be careful,
    so the tuple is the source and the string is derived from it.
    """
    s: str
    p: str
    o: str
    literal: bool


def triple(s: str, p: str, o: str, *, literal: bool = False) -> Stmt:
    _check_uri(s)
    _check_uri(p)
    if not literal:
        _check_uri(o)
    return Stmt(s, p, o, literal)


def render(st: Stmt) -> str:
    obj = f'"{esc(st.o)}"' if st.literal else f"<{st.o}>"
    return f"<{st.s}> <{st.p}> {obj} ."


def uri(local: str) -> str:
    return f"{EX}{local}"


def servicer_uri(name: str) -> str:
    return uri("abs-servicer-" + name.lower()
               .replace(" ", "-").replace(".", "").replace(",", ""))


def build_triples() -> list[Stmt]:
    reg = json.loads(REGISTRY.read_text())
    ext = {d["deal_id"]: d for d in json.loads(EXTRACT.read_text())["deals"]}

    triples: list[Stmt] = []
    seen: set[Stmt] = set()

    def add(t: Stmt) -> None:
        # Two deals share a servicer, so its type/label triples are generated
        # twice. RDF is a set, so the duplicate is harmless in the store --
        # but it would inflate the counts this task is verified on.
        if t not in seen:
            seen.add(t)
            triples.append(t)

    for deal in reg["deals"]:
        deal_id = deal["deal_id"]
        d_uri = uri(f"abs-deal-{deal_id}")
        # Explicitly typed for every role it is queried under -- there is no
        # inference to derive PoolBackedSecurity from AssetBackedSecurity.
        for cls in (C_ABS, C_POOL_BACKED):
            add(triple(d_uri, RDF_TYPE, cls))
        add(triple(d_uri, RDFS_LABEL, deal["legal_name"], literal=True))
        add(triple(d_uri, P_PROVENANCE, "public", literal=True))

        s_uri = servicer_uri(deal["servicer"])
        add(triple(s_uri, RDF_TYPE, C_SERVICER))
        add(triple(s_uri, RDFS_LABEL, deal["servicer"], literal=True))
        add(triple(s_uri, P_PROVENANCE, "public", literal=True))
        add(triple(d_uri, P_SERVICED_BY, s_uri))

        # `_check_uri` catches a URI built from a list or a string with
        # spaces, but "abs-tranche-None" is character-legal and silently
        # wrong. Resolving every parent against the deal's own tranche ids
        # catches that class too -- and a typo, and a cross-deal reference.
        tranche_ids = {t["tranche_id"] for t in ext[deal_id]["tranches"]}

        for t in ext[deal_id]["tranches"]:
            t_uri = uri(f"abs-tranche-{t['tranche_id']}")
            add(triple(t_uri, RDF_TYPE, C_TRANCHE))
            add(triple(t_uri, RDFS_LABEL,
                       f"{deal_id} Class {t['class_name']}", literal=True))
            add(triple(t_uri, P_PROVENANCE, t["provenance"], literal=True))
            # The pool collateralizes the tranche.
            add(triple(t_uri, P_IS_COLLATERALIZATION_OF, d_uri))
            # A LIST since Task 6 -- one edge per parent. Toyota's A-3 has two.
            for parent in t["subordinate_to"]:
                if parent not in tranche_ids:
                    raise ValueError(
                        f"{t['tranche_id']}: subordinate_to names "
                        f"{parent!r}, which is not a tranche of {deal_id}")
                add(triple(t_uri, P_IS_SUBORDINATE_TO,
                           uri(f"abs-tranche-{parent}")))

        filed = deal["prospectus_filed"]
        for trig in ext[deal_id]["triggers"]:
            g_uri = uri(f"abs-trigger-{trig['trigger_id']}")
            add(triple(g_uri, RDF_TYPE, C_TRIGGER_EVENT))
            add(triple(g_uri, RDFS_LABEL, trig["name"], literal=True))
            add(triple(d_uri, P_SPECIFIES_TRIGGER, g_uri))
            if trig["threshold_value"] is not None:
                add(triple(g_uri, P_THRESHOLD_VALUE,
                           trig["threshold_value"], literal=True))
            # The headline value is only the first component when the
            # definition is a sum. Emit every component so a consumer can see
            # the threshold is composite rather than assume it is not.
            for pct in trig["threshold_all_percents"]:
                add(triple(g_uri, P_THRESHOLD_COMPONENT, pct, literal=True))
            add(triple(g_uri, P_THRESHOLD_UNIT,
                       trig["threshold_unit"], literal=True))
            # In force from pricing, knowable from filing. Both are the 424B5
            # filing date for these deals. NEVER today's date -- see above.
            add(triple(g_uri, P_VALID_FROM, filed, literal=True))
            add(triple(g_uri, P_ASSERTED_AT, filed, literal=True))
            add(triple(g_uri, P_PROVENANCE, "public", literal=True))
            # Joins to the MongoDB `trigger_anchor` _id written by Task 8.
            add(triple(g_uri, P_ANCHOR,
                       f"{trig['trigger_id']}-anchor", literal=True))

    return triples


def _subjects_of_type(stmts: list[Stmt], cls: str) -> set[str]:
    return {st.s for st in stmts if st.p == RDF_TYPE and st.o == cls}


def _predicate_count(stmts: list[Stmt], pred: str) -> int:
    return sum(1 for st in stmts if st.p == pred)


#: Predicates another loader legitimately writes onto subjects this one owns,
#: so the retired-predicate sweep must not read them as drift. Named exactly,
#: never by prefix or namespace, so a SECOND unexplained foreign predicate
#: fails here instead of hiding behind the first -- the same discipline as the
#: cascade-signal exception in validators/partition.py.
#:
#: `ex:supersededBy` is Task 10's: the engineered amendment hangs off the
#: filed trigger node, and that trigger node is one of ours. Task 10 is its
#: single writer and this loader never asserts it. Measured 2026-08-23: it is
#: the ONLY such predicate, 1 pair out of 196.
FOREIGN_PREDICATES = {f"{EX}supersededBy"}


def ledger_conflicts(stmts: list[Stmt]) -> list[str]:
    """Refuse to write when the ledger already holds a DIFFERENT value.

    Set semantics make an identical re-run a no-op, which is what the
    idempotency check demonstrates. They do nothing at all for a *changed*
    source value. If `prospectus_extract.json` were regenerated with a
    corrected threshold or filing date, a re-run would INSERT a second,
    different-valued triple on the same subject and predicate. Fluree has no
    upsert-by-subject-predicate, so both assertions would live forever with
    nothing marking which supersedes which -- a silently ambiguous ledger,
    and unfixable.

    The comparison is per (subject, predicate) over the whole OBJECT SET, not
    per triple. A pair-wise check could not express Toyota's A-3, which
    legitimately has two `isSubordinatedTo` objects; a set comparison handles
    the multi-valued predicates (`rdf:type`, `ex:thresholdComponent`, the
    edges) and the single-valued ones under one rule.

    The rule is: whatever the ledger already holds for a (subject, predicate)
    must be a SUBSET of what this run asserts. Empty is fine -- a first load.
    Equal is fine -- a re-run. Anything the ledger holds that this run does
    not assert is drift: a changed value, a dropped tranche parent, a
    withdrawn component. This loader is the single writer for every one of
    these subjects, so there is no legitimate source for such a triple.

    It does NOT supersede. Superseding is Task 10's modelled operation --
    a new node plus `ex:supersedes` -- and must be a deliberate act, never a
    side effect of re-running a loader. This guard's job is to stop and name
    the disagreement for a human.

    KNOWN-ISSUES 17.4, CLOSED. The loop below iterates the INCOMING predicate
    set and queries only those predicates, so for most of this function's life
    a predicate the ledger held but the generator had stopped asserting was
    never queried at all -- its disappearance was invisible, and the docstring
    above framed the rule in exactly the way that hid it ("whatever the ledger
    holds for a (subject, predicate)" only ranges over pairs this run brings).
    The second sweep at the end closes that: it asks the ledger for EVERY
    predicate on this run's subjects and reports any this run asserts nowhere.
    """
    by_pred: dict[str, dict[str, set[tuple[bool, str]]]] = defaultdict(
        lambda: defaultdict(set))
    for st in stmts:
        by_pred[st.p][st.s].add((st.literal, st.o))

    conflicts: list[str] = []
    for pred, incoming in by_pred.items():
        # Scoped with VALUES to this loader's own subjects. An unscoped
        # `?s rdfs:label ?o` would drag back 9,405 rows of other waves'
        # labels to answer a question about 33 nodes.
        values = " ".join(f"<{s}>" for s in sorted(incoming))
        rows = fluree.query(
            f"SELECT ?s ?o FROM <{FLUREE_LEDGER_V2}> "
            f"WHERE {{ VALUES ?s {{ {values} }} ?s <{pred}> ?o }}"
        )["results"]["bindings"]
        for b in rows:
            subj = b["s"]["value"]
            held = (b["o"]["type"] != "uri", b["o"]["value"])
            if held not in incoming[subj]:
                kind = "literal" if held[0] else "uri"
                want = ", ".join(sorted(o for _, o in incoming[subj])) or "(none)"
                conflicts.append(
                    f"{subj}\n      predicate {pred}\n"
                    f"      ledger holds ({kind}): {held[1]!r}\n"
                    f"      this run asserts:     {want}")

    # Second sweep -- RETIRED PREDICATES. The loop above is driven by
    # `by_pred`, which comes from the incoming triples, so it can only ever
    # ask about predicates this run still asserts. This one runs the question
    # the other way round: everything the ledger holds on our subjects, minus
    # everything we assert.
    asserted = {(st.s, st.p) for st in stmts}
    subjects = sorted({st.s for st in stmts})
    if subjects:
        values = " ".join(f"<{s}>" for s in subjects)
        rows = fluree.query(
            f"SELECT DISTINCT ?s ?p FROM <{FLUREE_LEDGER_V2}> "
            f"WHERE {{ VALUES ?s {{ {values} }} ?s ?p ?o }}"
        )["results"]["bindings"]
        for b in rows:
            pair = (b["s"]["value"], b["p"]["value"])
            if pair in asserted or pair[1] in FOREIGN_PREDICATES:
                continue
            conflicts.append(
                f"{pair[0]}\n      predicate {pair[1]}\n"
                f"      ledger holds it; THIS RUN ASSERTS IT NOWHERE\n"
                f"      a predicate retired from the generator does not "
                f"disappear from an append-only ledger")
    return conflicts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path,
                    help="write the generated triples, one per line, to PATH")
    args = ap.parse_args()

    triples = build_triples()

    # Expectations are derived from the source files, not hardcoded, so this
    # is a comparison rather than a restatement of a constant.
    expect_tranches = len(_subjects_of_type(triples, C_TRANCHE))
    expect_edges = _predicate_count(triples, P_IS_SUBORDINATE_TO)

    print(f"  {len(triples)} triples")
    print(f"  {expect_tranches} tranche nodes, "
          f"{expect_edges} isSubordinatedTo edges")

    lines = [render(st) for st in triples]

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("\n".join(lines) + "\n")
        print(f"  wrote {args.out}")

    # Read-only, and it runs BEFORE any write. In a dry run a ledger that is
    # unreachable is a warning -- the point of --dry-run is to produce the
    # triple list for review, which does not need Fluree. In a real run it is
    # fatal: writing without having checked is the failure this guards.
    try:
        conflicts = ledger_conflicts(triples)
    except Exception as exc:
        if not args.dry_run:
            raise
        print(f"\n  WARNING: conflict check skipped, ledger unreachable: {exc}")
        conflicts = []

    if conflicts:
        print(f"\n  REFUSING TO WRITE -- {len(conflicts)} conflict(s). The "
              "ledger already holds a different value for:")
        for c in conflicts:
            print(f"    - {c}")
        print("\n  Nothing was written. Fluree is append-only, so inserting "
              "these would leave both values asserted with nothing marking\n"
              "  which supersedes which. Superseding is Task 10's modelled "
              "operation and must be deliberate -- resolve this by hand.")
        return 1

    if args.dry_run:
        print("\n  DRY RUN -- nothing written.")
        return 0

    BATCH = 500
    for i in range(0, len(lines), BATCH):
        fluree.update("INSERT DATA { " + " ".join(lines[i:i + BATCH]) + " }")

    # stable_scalar, not a bare query: a read immediately after INSERT DATA
    # can return 0 while the index catches up (known-issues.md §14.2). A bare
    # count here would produce a false FAIL as easily as a false PASS.
    # Every statement carries FROM -- Fluree 500s without it.
    n_tranche = fluree.stable_scalar(
        f"SELECT (COUNT(?t) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?t a <{C_TRANCHE}> }}")
    n_edges = fluree.stable_scalar(
        f"SELECT (COUNT(*) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?t <{P_IS_SUBORDINATE_TO}> ?s }}")
    print(f"  tranches in ledger: {n_tranche} (expected {expect_tranches})")
    print(f"  isSubordinatedTo in ledger: {n_edges} (expected {expect_edges})")

    if n_tranche != expect_tranches or n_edges != expect_edges:
        print("  FAIL: ledger disagrees with the generated triple set.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
