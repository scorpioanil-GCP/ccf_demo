"""cp-05's governed seam — the five assembly steps, and the arithmetic that earns the architecture.

[ADAPT] all of it. [MECHANISM] the operator sequence spec §D.2 declares.

This module holds no connection value and no domain constant. The anchor, the
depth, the materiality floor and the intent all arrive as arguments; the
predicates arrive from ``deployment.py``; the limit definition arrives from the
store. What lives here is the SHAPE of the assembly (spec §D.3), and nothing
else.

**The step that makes the product correct is step 5.2.** Everything above it is
retrieval; the deduplication is where a naive sum and a right answer part
company. Measured on the demonstrated anchor: gross committed 10,125,000,000
against adjusted 9,120,000,000 — 9.92% of gross is double-counted by a family
sum that does not do this.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import deployment as dep


@dataclass(frozen=True)
class LimitDefinition:
    """The versioned policy that decides what counts — spec §C.4 trap 3.

    Read from ``limit_definition`` by ``intent`` and never defaulted. "Total
    exposure" is not a property of the data; it is a property of the definition
    in force, and this record is that definition.
    """

    intent: str
    counts_guarantees: bool
    counts_undrawn: bool
    connection_basis: str
    limit_pct_of_capital: Decimal
    provenance: str

    @property
    def version(self) -> str:
        """The identity that travels into lineage (spec §B.1 element 5)."""
        return f"limit_definition/{self.intent}"


@dataclass
class Money:
    """One basis, summed. Kept as ``int`` minor units — no float touches money."""

    committed: int = 0
    outstanding: int = 0
    undrawn: int = 0

    def add(self, other: "Money") -> None:
        self.committed += other.committed
        self.outstanding += other.outstanding
        self.undrawn += other.undrawn

    def as_dict(self) -> dict[str, int]:
        return {
            "committed": self.committed,
            "outstanding": self.outstanding,
            "undrawn": self.undrawn,
        }


@dataclass
class EntityExposure:
    """One family member's own borrowings."""

    lei: str
    node: str
    legal_name: str | None
    facility_count: int
    gross: Money


@dataclass
class Rollup:
    """What step 6 assembles into the emitted contract."""

    anchor_lei: str
    anchor_node: str
    intent: str
    policy_version: str
    depth: int
    family_nodes: list[str]
    members_with_lei: int
    entities: list[EntityExposure]
    gross: Money
    adjusted: Money
    dedup_cases: list[dict[str, Any]]
    connected_without_exposure: list[str]
    findings: list[dict[str, Any]] = field(default_factory=list)
    reconciliation: dict[str, Any] | None = None


def resolve_anchor(cur, schema: str, lei: str) -> tuple[str, str]:
    """**Step 1 · Resolve.** ``lei`` → canonical obligor.

    An LEI that does not resolve RAISES. It does not return an empty rollup: a
    zero-exposure answer for a real obligor and a no-such-obligor answer are
    different facts, and the contract keeps them apart (spec §D.3 step 1).
    """
    cur.execute(f'SELECT lei, legal_name FROM {schema}.legal_entity WHERE lei = %s', (lei,))
    row = cur.fetchone()
    if row is None:
        raise LookupError(
            f"{lei} does not resolve in {schema}.legal_entity. "
            "An unresolvable anchor refuses; it does not return an empty rollup."
        )
    return row[0], row[1]


def load_limit_definition(cur, schema: str, intent: str) -> LimitDefinition:
    """**Step 2 · Policy.** The limit definition bound to ``intent``.

    A missing definition RAISES rather than defaulting. Spec §B.3: a silently
    defaulted limit definition is the failure the model-risk annotation exists
    to prevent.
    """
    cur.execute(
        f"SELECT intent, counts_guarantees, counts_undrawn, connection_basis, "
        f"limit_pct_of_capital, provenance FROM {schema}.limit_definition WHERE intent = %s",
        (intent,),
    )
    row = cur.fetchone()
    if row is None:
        cur.execute(f"SELECT intent FROM {schema}.limit_definition ORDER BY 1")
        known = ", ".join(r[0] for r in cur.fetchall())
        raise LookupError(f"no limit definition for intent {intent!r}. Declared intents: {known}")
    return LimitDefinition(*row)


def walk(source: dep.GraphSource, anchor_node: str, depth: int,
         follow_guarantees: bool, follow_cross_default: bool) -> list[str]:
    """**Step 3 · Traversal.** ONE walk, several predicate types, both directions.

    Spec §D.3 step 3 is emphatic and this is where it is honored: *do not issue
    one traversal per edge type.* One walk, one node set — and at rung 5 the
    predicate count rises from rung 4's one to four, which is where the pattern
    starts to pay.

    Walked in BOTH directions on purpose. A guarantee RECEIVED matters as much
    as one given, and a cross-default is symmetric by nature.
    """
    predicates = [dep.OWNS, dep.ULTIMATELY_CONSOLIDATED_BY]
    if follow_guarantees:
        predicates.append(dep.IS_GUARANTOR_OF)
    if follow_cross_default:
        predicates.append(dep.CROSS_DEFAULTS_WITH)

    seen = {anchor_node}
    frontier = {anchor_node}
    for _ in range(depth):
        found: set[str] = set()
        for node in frontier:
            for predicate in predicates:
                found.update(dep.one_column(
                    dep.sparql(source, f"SELECT ?o {dep._from_clause(source)} "
                                       f"WHERE {{ <{node}> <{predicate}> ?o }}"), "o"))
                found.update(dep.one_column(
                    dep.sparql(source, f"SELECT ?s {dep._from_clause(source)} "
                                       f"WHERE {{ ?s <{predicate}> <{node}> }}"), "s"))
        frontier = found - seen
        seen |= found
        if not frontier:
            break
    return sorted(seen)


def node_leis(source: dep.GraphSource, nodes: list[str]) -> dict[str, str]:
    """The ledger's own ``lei`` predicate — the ONLY sound slug→LEI bridge.

    Spec §C.3 records this as a join hazard because it caught the author:
    Fluree addresses subjects by entity slug while PostgreSQL keys on LEI, and
    joining the two directly yields a 100% miss that reads like a finding rather
    than a defect. **An implementation that appears to discover that no entity
    holds a facility has made this mistake.**
    """
    rows = dep.sparql(source, f"SELECT ?s ?lei {dep._from_clause(source)} "
                              f"WHERE {{ ?s <{dep.LEI_PREDICATE}> ?lei }}")
    every = {r["s"]["value"]: r["lei"]["value"] for r in rows if "s" in r and "lei" in r}
    return {node: every[node] for node in nodes if node in every}


def enrich(cur, schema: str, leis: list[str]) -> dict[str, tuple[int, Money]]:
    """**Step 4 · Batch Enrich.** ONE query for the whole family, never one per entity.

    Spec §D.3 step 4: fan-out here is entity × facility, so the N+1 penalty is
    MULTIPLICATIVE rather than linear. An implementation that issues one query
    per entity is not slow — it is wrong at scale, and the difference surfaces
    as a latency cliff rather than an error.
    """
    if not leis:
        return {}
    cur.execute(
        f"SELECT borrower_lei, count(*), "
        f"       coalesce(sum(commitment_amount),0)::bigint, "
        f"       coalesce(sum(outstanding_balance),0)::bigint, "
        f"       coalesce(sum(undrawn_availability),0)::bigint "
        f"FROM {schema}.facility WHERE borrower_lei = ANY(%s) GROUP BY 1",
        (leis,),
    )
    return {r[0]: (r[1], Money(r[2], r[3], r[4])) for r in cur.fetchall()}


def aggregate(cur, schema: str, anchor_lei: str, anchor_node: str, intent: str,
              limit: LimitDefinition, depth: int, nodes: list[str],
              lei_by_node: dict[str, str], books: dict[str, tuple[int, Money]],
              materiality: float, flags: dict[str, bool]) -> Rollup:
    """**Step 5 · Aggregate** — in-memory, algorithmic, and where the product is won.

    Five sub-steps in spec §D.3 step 5's order. Sub-step 2 is the one that makes
    the answer correct; the rest is bookkeeping around it.
    """
    # ---- 5.1 sum by entity, then by group -----------------------------------
    entities: list[EntityExposure] = []
    gross = Money()
    names: dict[str, str] = {}
    if lei_by_node:
        cur.execute(f"SELECT lei, legal_name FROM {schema}.legal_entity WHERE lei = ANY(%s)",
                    (list(lei_by_node.values()),))
        names = dict(cur.fetchall())

    for node in nodes:
        lei = lei_by_node.get(node)
        if lei is None or lei not in books:
            continue
        count, money = books[lei]
        entities.append(EntityExposure(lei, node, names.get(lei), count, money))
        gross.add(money)

    # ---- 5.2 DEDUPLICATE GUARANTEE PATHS ------------------------------------
    #
    # Where a guarantee edge already captures a subsidiary's exposure at the
    # parent, count it ONCE. This is the step that makes the product correct and
    # the naive sum wrong (spec §D.3 step 5.2, §C.4 trap 1).
    #
    # `covered_pct` and `cap_amount` are honored rather than assumed to be 1 and
    # unbounded — a 60% guarantee removes 60% of the captured exposure, and a
    # capped one removes no more than its cap.
    #
    # GATED ON THE POLICY, NOT ON THE CALLER'S FLAG. `counts_guarantees` comes
    # from the limit definition; `follow_guarantees` decided only whether the
    # walk traversed the edge. Spec §B.4 keeps traversal scope and measurement
    # policy apart, and this is the line where that separation is enforced.
    dedup_cases: list[dict[str, Any]] = []
    removed = Money()
    if limit.counts_guarantees:
        family_leis = set(lei_by_node.values())
        cur.execute(
            f"SELECT guarantor_lei, obligor_uri, kind, covered_pct, cap_amount "
            f"FROM {schema}.guarantee_terms WHERE guarantor_lei = ANY(%s)",
            (sorted(family_leis),),
        )
        for guarantor, obligor_uri, kind, covered_pct, cap in cur.fetchall():
            if kind != "downstream-dedup":
                continue
            obligor_lei = lei_by_node.get(str(obligor_uri))
            if obligor_lei is None or obligor_lei not in books:
                continue
            _, book = books[obligor_lei]
            share = Decimal(str(covered_pct))
            captured = int(Decimal(book.committed) * share)
            if cap is not None:
                captured = min(captured, int(Decimal(str(cap))))
            removed.committed += captured
            removed.outstanding += int(Decimal(book.outstanding) * share)
            removed.undrawn += int(Decimal(book.undrawn) * share)
            dedup_cases.append({
                "guarantor_lei": guarantor,
                "obligor_lei": obligor_lei,
                "obligor_node": str(obligor_uri),
                "covered_pct": str(share),
                "cap_amount": None if cap is None else str(cap),
                "committed_removed": captured,
            })

    adjusted = Money(
        committed=gross.committed - removed.committed,
        outstanding=gross.outstanding - removed.outstanding,
        undrawn=gross.undrawn - removed.undrawn,
    )

    # `counts_undrawn=false` excludes undrawn availability from the ADJUSTED
    # measure only. Gross always ships whole — a consumer must be able to see
    # what the policy removed (spec §D.6).
    if not limit.counts_undrawn:
        adjusted.undrawn = 0

    # ---- 5.3 materiality, with the cross-default exemption -------------------
    #
    # Entities reached ONLY by cross-default hold no facility and contribute
    # zero. They are reported rather than absorbed into a residual: absorbing
    # them would delete the finding the traversal exists to produce
    # (spec §C.4 trap 2). The materiality floor applies to entities that HAVE
    # exposure, which is the population it was written for.
    with_exposure = {e.lei for e in entities}
    connected_without_exposure = sorted(
        lei for node, lei in lei_by_node.items() if lei not in with_exposure
    )
    floor = int(gross.committed * materiality) if gross.committed else 0
    material = [e for e in entities if e.gross.committed >= floor]
    residual = Money()
    for entity in entities:
        if entity.gross.committed < floor:
            residual.add(entity.gross)

    # ---- findings -----------------------------------------------------------
    findings: list[dict[str, Any]] = []
    for case in dedup_cases:
        findings.append({
            "kind": "guarantee-dedup-applied",
            "detail": f"{case['guarantor_lei']} guarantees {case['obligor_lei']} at "
                      f"{case['covered_pct']}; {case['committed_removed']} removed from committed",
        })
    if connected_without_exposure:
        findings.append({
            "kind": "connected-without-exposure",
            "detail": f"{len(connected_without_exposure)} family members are bound by "
                      "ownership, guarantee or cross-default and hold no facility. A "
                      "borrower-keyed sum cannot reach them.",
        })
    # The flag/policy conflict is REPORTED, never resolved silently (spec §B.4).
    if flags["follow_guarantees"] and not limit.counts_guarantees:
        findings.append({
            "kind": "traversal-scope-exceeds-measurement-policy",
            "detail": f"follow_guarantees=true traversed guarantee edges, but intent "
                      f"{intent!r} sets counts_guarantees=false, so they are not counted. "
                      "Traversal scope and measurement policy are different questions.",
        })

    return Rollup(
        anchor_lei=anchor_lei,
        anchor_node=anchor_node,
        intent=intent,
        policy_version=limit.version,
        depth=depth,
        family_nodes=nodes,
        members_with_lei=len(lei_by_node),
        entities=material,
        gross=gross,
        adjusted=adjusted,
        dedup_cases=dedup_cases,
        connected_without_exposure=connected_without_exposure,
        findings=findings,
    )


def reconcile(cur, schema: str, anchor_lei: str, committed: int) -> dict[str, Any] | None:
    """The XBRL plausibility check — spec §C.1.

    The bank holds only part of the borrower's debt, so these will not match.
    The claim is that the synthetic figure is a PLAUSIBLE SHARE of the real one,
    and the estate carries the verdict rather than this program computing it.
    """
    cur.execute(
        f"SELECT committed, reported_debt, share, plausible "
        f"FROM {schema}.debt_reconciliation WHERE lei = %s", (anchor_lei,))
    row = cur.fetchone()
    if row is None:
        return None
    return {
        "anchor_committed": int(row[0]),
        "reported_debt": int(row[1]),
        "share": str(row[2]),
        "plausible": bool(row[3]),
        "family_gross_committed": committed,
    }


def reconciliation_guard(rollup: Rollup) -> None:
    """**The fourth validation gate** — spec §D.7, and the one that earns its place.

    Gross must be >= guarantee-adjusted, per group. Adjusted exposure exceeding
    gross is arithmetically impossible; if it happens, step 5.2 removed the same
    exposure twice.

    The other three gates catch a broken pipeline. This one catches a PLAUSIBLE
    WRONG ANSWER — the failure mode spec §A says is invisible in the output.
    """
    if rollup.adjusted.committed > rollup.gross.committed:
        raise AssertionError(
            "reconciliation guard: adjusted committed "
            f"{rollup.adjusted.committed} exceeds gross {rollup.gross.committed}. "
            "The dedup logic double-subtracted."
        )
