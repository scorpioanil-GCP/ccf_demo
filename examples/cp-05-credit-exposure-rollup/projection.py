"""cp-05's Π — L5 decides what of the family's truth is relevant to THIS caller.

[ADAPT] all of it. [MECHANISM] `ccf.projection.plan::ProjectionPlan`, which this
class implements structurally rather than by inheritance (`CLAUDE.md` §11).

**The semantic boundary this module exists to hold:**

> The assembler determines the complete family exposure truth.
> L5 decides which of that truth is relevant to this caller's decision.

The materiality threshold is a **presentation preference**, not a fact about the
family. Two callers asking at 2% and 10% are owed the SAME underlying truth —
the same 77-entity family, the same gross, the same guarantee-adjusted total —
and different *material sets*. Applying the threshold inside the assembler would
let a request parameter alter truth rather than shape context, and the two
callers would then disagree about what the borrower owes.

**The invariant, measured across 2% / 5% / 10%:** family 77, gross
10,125,000,000 and adjusted 9,325,000,000 are IDENTICAL; only the material set
(4 / 4 / 3) and the content address move.

**ONE AUTHORITY FOR THE OPERATOR REQUIREMENT.** The plan is handed the set
`ccf_config.yaml::product_class.required_operator_keys` declares; it authors no
second copy. cp-05 is a one-document deployment for operator requirements (Dave,
2026-09-08) and is on `RULED_ONE_DOCUMENT_DEPLOYMENTS` for that reason.

**L5 is not told who won, and that is deliberate.** The plan receives the
EFFECTIVE threshold and applies it. Whether that value was the product default,
this caller's choice or a policy ceiling is recorded on the contract's effective
request (spec §B.4.1) and travels into replay — it is an audit fact, not an
input to the projection's decision. A projection that branched on authority
would be letting provenance change the answer.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping, Sequence

from ccf.projection.plan import Perspective, ProjectionOutput


class ExposureRollupProjection:
    """Split the family's complete exposure into what this caller is shown.

    Constructed PER REQUEST with the effective threshold, because
    `ProjectionPlan.invoke` receives ``view``, ``operator_outputs``,
    ``perspective`` and ``temporal_boundary`` and **no request** — a
    caller-selectable projection parameter has no declared channel into
    `invoke`, so it arrives through the constructor. Recorded as friction in
    spec §F.4 rather than worked around silently; it is not a defect, but an
    author has to discover it.
    """

    def __init__(self, *, plan_id: str, required: Sequence[str], threshold: Decimal,
                 entities: Sequence[Any], gross_committed: int,
                 connected_without_exposure: Sequence[str],
                 business: Mapping[str, Any] | None = None) -> None:
        self._plan_id = plan_id
        self._required = tuple(required)
        self._threshold = threshold
        self._entities = list(entities)
        self._gross_committed = gross_committed
        self._connected = list(connected_without_exposure)
        # ASSEMBLED TRUTH, CARRIED THROUGH — never computed here (`D-IMPL-299`).
        #
        # On the canonical path the served product's payload IS this plan's
        # `ProjectionOutput.payload`, so cp-05's business answer — the family,
        # the gross and adjusted measures, the findings, the reconciliation —
        # has to reach the caller through it. It arrives ALREADY DETERMINED,
        # from `assembler.aggregate` before Π ran, and this class does not add,
        # re-derive or adjust a single figure in it.
        #
        # Dave's refinement, and the reason this is a pass-through rather than
        # a computation: *"If aggregation is part of determining $10.125B /
        # $9.325B, it must remain before Π as assembly/operator logic.
        # Otherwise we solve the Postgres problem but still let L5 construct
        # truth."* The threshold work below reads `entities` and
        # `gross_committed`; it never reads this mapping.
        self._business = dict(business or {})

    @property
    def plan_id(self) -> str:
        """Stable identity of this plan; binds the product to its Π."""
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        """The declared set, HANDED IN — never a second copy authored here.

        **ONE AUTHORITY FOR THIS DEPLOYMENT'S OPERATOR REQUIREMENT, and that is
        a ruling** (Dave, 2026-09-08): *"cp-05 is a one-document deployment for
        operator requirements. The Control Plane/product-class declaration is
        authoritative; the projection plan derives its required operator set
        from that declaration."* It is the shape `cp-00` through `cp-04` already
        use and that `RULED_ONE_DOCUMENT_DEPLOYMENTS` names.

        **What this replaces, recorded because the correction matters more than
        the line.** An earlier revision returned a hard-coded tuple here. That
        made cp-05 a TWO-document deployment — `ccf_config.yaml`'s
        `required_operator_keys` and this tuple — with nothing comparing them.
        Measured: dropping one operator from that tuple served a product having
        run ONE operator while the Control Plane claimed two, with every gate
        green and lineage honestly reporting one. The deeper defect was not a
        missing `refuse_operator_set_divergence` call; it was creating a second
        authority the established pattern already avoids
        (`CP-SPEC-005` §F.4 finding 20).

        `ProjectionPlanFactoryProtocol` states the same thing about its own
        `required` argument: *"Passed in rather than read by the plan, so a
        deployment authoring one operator set cannot accidentally author a
        second one for Gate 2 to diverge from."*

        Order is not significant — the engine imposes Policy → Similarity →
        Temporal → Traversal, and declaring an order here would let a plan
        reorder Policy after Similarity, the one ordering the fabric may never
        permit (INV-CH7-26).
        """
        return self._required

    def invoke(self, *, view: Any, operator_outputs: Mapping[str, Any],
               perspective: Perspective, temporal_boundary: datetime) -> ProjectionOutput:
        """Apply the effective threshold. Truth in, relevance out."""
        # DECIMAL ARITHMETIC ON A MONEY FIGURE. `int(10_125_000_000 * 0.05)`
        # is right by luck; the same expression at other thresholds is not, and
        # a floor computed in binary floating point would move a borrower
        # across the materiality line differently on different machines.
        floor = (int(self._gross_committed * self._threshold)
                 if self._gross_committed else 0)

        material = [e for e in self._entities if e.gross.committed >= floor]
        residual = {"committed": 0, "outstanding": 0, "undrawn": 0}
        residual_count = 0
        for entity in self._entities:
            if entity.gross.committed < floor:
                residual["committed"] += entity.gross.committed
                residual["outstanding"] += entity.gross.outstanding
                residual["undrawn"] += entity.gross.undrawn
                residual_count += 1

        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                # Assembled truth first, untouched; relevance after it.
                **self._business,
                "threshold": str(self._threshold),
                "floor_committed": floor,
                "material": [
                    {"lei": e.lei, "legal_name": e.legal_name,
                     "facilities": e.facility_count, "gross": e.gross.as_dict()}
                    for e in material
                ],
                "residual": residual,
                "residual_entities": residual_count,
                # `entities` is `material` under the name the renderer and
                # `expected.yaml` both use. One list, two readers, no second
                # derivation.
                "entities": [
                    {"lei": e.lei, "legal_name": e.legal_name,
                     "facilities": e.facility_count, "gross": e.gross.as_dict()}
                    for e in material
                ],
                # NEVER absorbed into the residual, whatever the threshold.
                # These entities hold no facility and are reached only by
                # guarantee or cross-default; summarizing them away would delete
                # the finding the traversal exists to produce (spec §C.4 trap 2).
                "connected_without_exposure": self._connected,
            },
        )
