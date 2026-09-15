"""Π — the spread this product serves, read off the GRAPH VIEW.

[ADAPT] everything. [MECHANISM] the two Protocol members: `required_operators`
and `invoke`. Π is deployment code by construction (whitepaper §7.5); the
fabric constructs this class and calls it, and never rewrites what it does.

**Everything served here is read off the GRAPH VIEW the resolver hands in.**
Not off the acquisition result, not off a scenario object carried in from the
side. The obligor, every period, every line and every cohort statistic became
fabric state at L2, each dated from the filing that asserted it; they were
shaped by the policy envelope at L4; and what survives is what a consumer is
told. Reading around the view would serve rows the policy operator excluded —
which is exactly what the frozen specimen's Π did, and why an obligor it
suppressed still had its spread in memory.

**Π IS NOT ROLE-CONDITIONING AT THIS TIER.** Every authorized caller gets the
same SHAPE. What differs per principal is WHICH OBLIGORS EXIST to be shaped,
and that is settled upstream by the Policy operator. The `obligor: None` this
projection emits for an empty view is the product's own gate's to refuse — one
text for an obligor that does not exist and one the principal may not see.

**PER-ATTRIBUTE, NOT PER PRODUCT.** Every reported line carries the
`filed_date` and `accession` of the filing that asserted THAT figure, its own
`basis_applied` and its own restatement marking — read off the line entity,
which carries them as its own attributes because they are its own facts.

**NO FIGURE IS EVER `0` FOR "ABSENT"**; the word `NOT_EVALUABLE` is served.
**DECIMALS ARE SERVED AS TEXT**: a float is not bit-stable and cannot appear in
a content address; text is the one representation stable in the hash AND
renderable by a client.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput

#: The vocabulary this Π reads — declared once in `deployment.py`, read here.
CLASS_OBLIGOR = "obligor"
CLASS_PERIOD = "spread_period"
CLASS_LINE = "spread_line"
CLASS_COHORT = "peer_cohort"
INPUTS_SEPARATOR = "|"
NOT_EVALUABLE = "NOT_EVALUABLE"
ANCHOR_MEMBER = "latest_filed_in_payload"
LEI = "lei"


def _line(attributes: Mapping[str, str]) -> dict[str, Any]:
    """One line as the §D.6 contract emits it — reported or derived."""
    if attributes.get("derived") == "true":
        return {
            "value": attributes["value"],
            "unit": attributes["unit"],
            "derived": True,
            # COLLECTED DURING EVALUATION, not copied from the artifact's
            # declared `inputs:` list — the two differ wherever a `??` fallback
            # took one branch.
            "inputs": [name for name in attributes.get("inputs", "").split(INPUTS_SEPARATOR) if name],
        }
    if attributes.get("reason"):
        # The line is declared and this period filed none of its tags. A real
        # completeness shortfall, served as the word rather than a default.
        return {
            "value": NOT_EVALUABLE,
            "unit": NOT_EVALUABLE,
            "kind": attributes["kind"],
            "derived": False,
            "reason": attributes["reason"],
        }
    return {
        "value": attributes["value"],
        "unit": attributes["unit"],
        # INSTANT VERSUS DURATION IS VISIBLE: a payload showing only durations
        # would be a spread with no balance sheet in it.
        "kind": attributes["kind"],
        "period_start": attributes.get("period_start") or None,
        "period_end": attributes["period_end"],
        # WHICH FILING ASSERTED THIS FIGURE — the two columns that make the
        # lineage per-attribute rather than per-product.
        "filed_date": attributes["filed_date"],
        "accession": attributes["accession"],
        "form": attributes["form"],
        "basis_applied": attributes["basis_applied"],
        # THE VALUE CHANGED ACROSS FILINGS ON THE FULL KEY — never inferred
        # from accession multiplicity.
        "restated": attributes["restated"] == "true",
        "restatement_class": attributes["restatement_class"],
        # THE FILER FILED THIS LINE THE OTHER WAY ROUND FROM ITS DECLARATION.
        # Marked, never silently reinterpreted.
        "kind_conflict": attributes["kind_conflict"] == "true",
        "derived": False,
    }


class FinancialSpreadProjection:
    """Shape the admitted spread into the §D.6 emitted contract."""

    def __init__(self, *, plan_id: str, required: tuple[str, ...], subject: str) -> None:
        self._plan_id = plan_id
        # The SDK-supplied operator set, held exactly as handed in. This
        # projection authors no operator set of its own and has none to author.
        self._required = required
        # THE OBLIGOR THIS QUESTION IS ABOUT, from the EFFECTIVE request the
        # SDK hands the plan factory. Π serves the subject's claims and no
        # other's: a view holding a second obligor — a shared fabric, a stale
        # run — cannot be served as this one's spread, and an anchor that
        # resolved to nothing finds nothing here whatever else the view holds.
        self._subject = subject

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        """The set the SDK supplied, returned unchanged."""
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        by_class: dict[str, list[Any]] = defaultdict(list)
        for record in view.entities:
            if record.claim.attributes.get(LEI) == self._subject:
                by_class[record.claim.entity_class].append(record)

        obligors = by_class.get(CLASS_OBLIGOR, [])
        if not obligors:
            # THE POLICY OPERATOR REMOVED IT, or it never existed. §B.2's
            # suppression rule: no count, no marker, no placeholder, and no way
            # to tell this apart from an obligor that does not exist.
            return ProjectionOutput(
                plan_id=self._plan_id,
                payload={"obligor": None, "perspective_role": perspective.role},
            )
        record = obligors[0]
        attributes = record.claim.attributes

        # Periods, newest first, keyed `(period_end, fiscal_period)`.
        periods = sorted(
            by_class.get(CLASS_PERIOD, []),
            key=lambda r: (r.claim.attributes["period_end"], r.claim.attributes["fiscal_period"]),
            reverse=True,
        )
        lines_by_period: dict[tuple[str, str], dict[str, Any]] = defaultdict(dict)
        for line in by_class.get(CLASS_LINE, []):
            a = line.claim.attributes
            lines_by_period[(a["period_end"], a["fiscal_period"])][a["line"]] = _line(a)

        filed = [
            r.claim.attributes["latest_filed"]
            for r in periods
            if r.claim.attributes.get("latest_filed") not in (None, "", NOT_EVALUABLE)
        ]

        cohort_by_period: dict[str, dict[str, Any]] = defaultdict(dict)
        for statistic in by_class.get(CLASS_COHORT, []):
            a = statistic.claim.attributes
            cohort_by_period[a["period_end"]][a["tag"]] = {
                "peers_reporting": int(a["peers_reporting"]),
                "median": a["median"],
            }
        peer_comparison: Any = (
            {
                "cohort_basis": attributes["peer_cohort_basis"],
                "sic": attributes["peer_sic"],
                "cohort_size": int(attributes["peer_cohort_size"]),
                "by_period": [
                    {"period_end": period_end, "tags": dict(sorted(tags.items()))}
                    for period_end, tags in sorted(cohort_by_period.items(), reverse=True)
                ],
            }
            if cohort_by_period
            else NOT_EVALUABLE
        )

        payload: dict[str, Any] = {
            "obligor": {
                "lei": attributes["lei"],
                # The canonical URI L2 minted — the fabric's own name for this
                # obligor, which exists only because the write path ran.
                "entity_id": record.claim.entity_uri,
                "cik": int(attributes["cik"]),
                "obligor_legal_name": attributes["obligor_legal_name"] or None,
                # The attribute Policy filtered on, RETURNED as well as filtered
                # on: a product that filters on a field it does not return
                # cannot be audited from its own payload.
                "obligor_jurisdiction": attributes["obligor_jurisdiction"],
                "fiscal_year_end_month": (
                    int(attributes["fiscal_year_end_month"]) if attributes["fiscal_year_end_month"] else None
                ),
                "latest_filed_date": attributes["latest_filed_date"],
                # AN ITEM 4.02 EXISTS — CORROBORATION ONLY, served beside the
                # per-line `restated` marking, never instead of it.
                "formally_restated": attributes["formally_restated"] == "true",
            },
            # WHICH OF THE TWO TRUTHS THIS WHOLE PAYLOAD IS.
            "basis_applied": attributes["basis_applied"],
            # THE FRESHEST FILING ANY SERVED FIGURE RESTS ON — the declared TTL
            # anchor, served as a fact so the product's own gate and a reader
            # can hold the window against it.
            ANCHOR_MEMBER: max(filed) if filed else NOT_EVALUABLE,
            "periods": [
                {
                    "period_end": r.claim.attributes["period_end"],
                    "fiscal_period": r.claim.attributes["fiscal_period"],
                    # WHICH λ_c THIS COLUMN DECAYS AGAINST.
                    "signal_class": r.claim.attributes["signal_class"],
                    "latest_filed": r.claim.attributes["latest_filed"],
                    "lines": dict(
                        sorted(
                            lines_by_period[
                                (r.claim.attributes["period_end"], r.claim.attributes["fiscal_period"])
                            ].items()
                        )
                    ),
                }
                for r in periods
            ],
            "peer_comparison": peer_comparison,
            "perspective_role": perspective.role,
        }
        return ProjectionOutput(plan_id=self._plan_id, payload=payload)


def plan_class() -> type[FinancialSpreadProjection]:
    """Π as a class the fabric constructs, never an object it is handed."""
    return FinancialSpreadProjection
