"""Π — what actually secures this exposure, conditioned for the credit role.

[ADAPT] everything. [MECHANISM] the two Protocol members, `required_operators`
and `invoke`. Π is deployment code by construction (whitepaper §7.5); the fabric
constructs this class and calls it, and never rewrites what it does.

**Everything served is read off the GraphView the resolver hands in** — not off
the acquisition result. The two legs' facts became fabric state at L2, the
policy envelope and the walk shaped them at L4, and what survives is what a
consumer is told. Reading around the view would serve rows policy excluded.

## The allocation, and why it is Π's rather than an operator's

§D step 5 is *in-memory, algorithmic*: apply haircuts, allocate shared assets by
the caller's mode, filter set-off by enforceability, emit the three measures.
None of that is a graph read, so none of it is an operator — and a step that
carries a Standard verb but is not a registered operator does not enter
`operators_invoked`.

**Priority allocation is the whole product.** Under `priority` a junior position
receives only the residual after senior claims against the same asset; under
`pro-rata` value splits by exposure share. The two disagree exactly where the
graph carries a subordinate lien — which a collateral column cannot express, and
which is §A's counterfactual stated as arithmetic.

**The over-allocation guard** (§D validation gates, the fourth beyond the SDK's
three): the sum of allocations against any single asset must not exceed its
haircut value. It is computed here and returned as a finding rather than raised,
because the product gate is where a refusal belongs.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput

HERE = Path(__file__).parent

KIND = "node_kind"


def declaration() -> Mapping[str, Any]:
    document: Mapping[str, Any] = yaml.safe_load(
        (HERE / "artifacts" / "projection.yaml").read_text(encoding="utf-8"))
    return document["declaration"]


def _decimal(value: str | None) -> Decimal:
    return Decimal(value) if value else Decimal(0)


class CollateralCoverageProjection:
    """Coverage, priority-adjusted coverage, and what is unencumbered."""

    def __init__(self, *, plan_id: str, required: tuple[str, ...],
                 declared: Mapping[str, Any], anchor: str,
                 commitment: Decimal, apply_haircuts: bool,
                 shared_collateral: str, jurisdiction_basis: str,
                 enforceable_jurisdictions: frozenset[str]) -> None:
        self._plan_id = plan_id
        # The SDK-supplied operator set, held exactly as handed in. This
        # projection authors no operator set of its own.
        self._required = required
        self._declared = declared
        self._anchor = anchor
        self._commitment = commitment
        # Every one of these is the EFFECTIVE value: `GovernedResolver` hands
        # the plan factory the effective request, after class defaults and
        # policy have folded. None is a raw caller value.
        self._apply_haircuts = apply_haircuts
        self._shared_collateral = shared_collateral
        self._jurisdiction_basis = jurisdiction_basis
        self._enforceable = enforceable_jurisdictions

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def _rank(self, position: str | None) -> int:
        seniority = self._declared["allocation"]["seniority"]
        if position and position in seniority:
            return int(seniority[position])
        return int(self._declared["allocation"]["unknown_rank"])

    def invoke(self, *, view: GraphView, operator_outputs: Mapping[str, OperatorOutput],
               perspective: Perspective, temporal_boundary: datetime) -> ProjectionOutput:
        by_kind: dict[str, list[Any]] = {}
        for record in view.entities:
            by_kind.setdefault(record.claim.attributes.get(KIND, ""), []).append(record)

        # An entity URI is a content hash. Everything below reasons in the
        # SOURCE's ids, so the map is built once and used everywhere — the
        # alternative is comparing a readable anchor id against a hash, which
        # matches nothing and reports every asset as shared.
        ref_of = {r.claim.entity_uri: r.claim.attributes.get("ref", r.claim.entity_uri)
                  for r in view.entities}

        # (facility, asset) -> lien position, read from the REIFIED pledges.
        # This is what lets a junior claim be ranked against a senior one; the
        # asset alone carries only the anchor's own position.
        position_of: dict[tuple[str, str], str | None] = {}
        for record in by_kind.get("pledge", []):
            label = record.claim.attributes.get("label", "")
            facility, _, asset = label.partition(" / ")
            position_of[(facility, asset)] = (
                record.claim.attributes.get("lien_position") or None)

        # --- what secures the anchor, and who else has a claim on it --------
        secured: dict[str, set[str]] = {}
        for record in view.relationships:
            if record.claim.relationship_type == "securedBy":
                secured.setdefault(ref_of.get(record.claim.object_uri, ""), set()).add(
                    ref_of.get(record.claim.subject_uri, ""))

        assets = []
        for record in sorted(by_kind.get("asset", []),
                             key=lambda r: r.claim.entity_uri):
            a = record.claim.attributes
            valuation = _decimal(a.get("valuation"))
            haircut = _decimal(a.get("haircut"))
            # The haircut is applied HERE, at Π, so the graph read is identical
            # for both settings and only the payload — and therefore the
            # content address — differs.
            realizable = valuation * (Decimal(1) - haircut) if self._apply_haircuts \
                else valuation
            asset_ref = ref_of.get(record.claim.entity_uri, record.claim.entity_uri)
            claimants = sorted(secured.get(asset_ref, ()))
            assets.append({
                "uri": asset_ref,
                "category": a.get("category") or None,
                "description": a.get("label") or None,
                "valuation": str(valuation),
                # PER ASSET, never one product-level freshness. §6.4 Temporal
                # Validation refuses to let a product flatten a one-day mark
                # and a one-year appraisal into a single figure.
                "valuation_date": a.get("valuation_date") or None,
                "valuation_age_days": int(a.get("valuation_age_days") or 0),
                "haircut": str(haircut),
                "realizable_value": str(realizable),
                "lien_position": a.get("lien_position") or None,
                "shared_with": [c for c in claimants if c != self._anchor],
                "provenance": a.get("provenance") or None,
            })

        # --- allocate assets shared across facilities -----------------------
        allocations: dict[str, Decimal] = {}
        for asset in assets:
            claimants = sorted({self._anchor, *asset["shared_with"]})
            realizable = Decimal(asset["realizable_value"])
            if len(claimants) == 1:
                allocations[asset["uri"]] = realizable
                asset["allocation_basis"] = "sole"
                asset["allocated_to_anchor"] = str(realizable)
                continue
            if self._shared_collateral == "pro-rata":
                share = realizable / Decimal(len(claimants))
                allocations[asset["uri"]] = share
                asset["allocation_basis"] = f"pro-rata across {len(claimants)}"
            else:
                # PRIORITY: a junior position receives only the residual after
                # senior claims against the same asset. This is the line a
                # collateral column cannot express.
                mine = self._rank(position_of.get((self._anchor, asset["uri"])))
                senior = sum(
                    1 for c in claimants if c != self._anchor
                    and self._rank(position_of.get((c, asset["uri"]))) < mine)
                allocations[asset["uri"]] = (
                    realizable if senior == 0 else Decimal(0))
                asset["allocation_basis"] = (
                    "senior" if senior == 0 else f"residual behind {senior}")
            asset["allocated_to_anchor"] = str(allocations[asset["uri"]])

        # --- set-off, filtered by the basis the caller asked for ------------
        setoff = []
        for record in sorted(by_kind.get("deposit", []),
                             key=lambda r: r.claim.entity_uri):
            a = record.claim.attributes
            contractual = a.get("setoff_contractual") == "true"
            enforceable = a.get("setoff_enforceable") == "true"
            counts = contractual if self._jurisdiction_basis == "contractual" \
                else (contractual and enforceable)
            setoff.append({
                "uri": ref_of.get(record.claim.entity_uri, record.claim.entity_uri),
                "balance": a.get("balance") or "0",
                "currency": a.get("currency") or None,
                "jurisdiction": a.get("jurisdiction") or None,
                "contractual": contractual,
                "enforceable": enforceable,
                "counted": counts,
            })

        # --- the public register --------------------------------------------
        filings = [
            {
                "filing_number": r.claim.attributes.get("filing_number"),
                "debtor_of_record": r.claim.attributes.get("debtor_of_record"),
                "filed_on": r.claim.attributes.get("filed_on") or None,
                "lapses_on": r.claim.attributes.get("lapses_on") or None,
                "filing_status": r.claim.attributes.get("filing_status") or None,
                # The register's own words, in order, because an amendment's
                # action is not scalar.
                "amendment_actions": [
                    s for s in (r.claim.attributes.get("amendment_action") or "").split(" | ") if s],
                "state": r.claim.attributes.get("label"),
            }
            for r in sorted(by_kind.get("ucc_filing", []),
                            key=lambda r: r.claim.entity_uri)
        ]

        collateral_value = sum(allocations.values(), Decimal(0))
        setoff_value = sum((Decimal(d["balance"]) for d in setoff if d["counted"]),
                           Decimal(0))
        total = collateral_value + setoff_value
        ratio = (total / self._commitment) if self._commitment else Decimal(0)

        # --- the fourth validation gate, computed as a finding ---------------
        over = [
            {"uri": a["uri"], "haircut_value": a["realizable_value"],
             "allocated": str(allocations[a["uri"]])}
            for a in assets
            if allocations[a["uri"]] > Decimal(a["realizable_value"])
        ]

        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "facility": self._anchor,
                "commitment": str(self._commitment),
                "basis": {
                    "apply_haircuts": self._apply_haircuts,
                    "shared_collateral": self._shared_collateral,
                    "jurisdiction_basis": self._jurisdiction_basis,
                },
                "coverage": {
                    "collateral_value": str(collateral_value),
                    "setoff_value": str(setoff_value),
                    "total": str(total),
                    "coverage_ratio": str(ratio),
                    "unencumbered_value": str(
                        max(Decimal(0), total - self._commitment)),
                    "shortfall": str(max(Decimal(0), self._commitment - total)),
                },
                "assets": assets,
                "setoff": setoff,
                "ucc_filings": filings,
                "findings": {
                    "shared_assets": sum(1 for a in assets if a["shared_with"]),
                    "unpositioned_pledges": sum(
                        1 for a in assets if a["lien_position"] is None),
                    "setoff_excluded_as_unenforceable": sum(
                        1 for d in setoff if d["contractual"] and not d["enforceable"]),
                    "terminated_liens": sum(
                        1 for f in filings if "Termination" in f["amendment_actions"]),
                    "over_allocated_assets": over,
                },
            },
        )


def plan_class() -> type[CollateralCoverageProjection]:
    """Π as a class the fabric constructs, never an object it is handed."""
    return CollateralCoverageProjection
