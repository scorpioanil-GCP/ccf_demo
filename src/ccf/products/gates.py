"""The three validation gates — the only construction path of a product.

Whitepaper §7.6 (INV-CH7-46 empty-operator guard, INV-CH7-47 lineage strict
equality, INV-CH7-48 TTL bounds; INV-CH7-52 the canonical sequence running
before any cache write or delivery); DESIGN.md §2B.3 and §9.

The sequence is fixed and it is an order, not a set:

1. **empty-operator guard** — a product whose ``operators_invoked`` is empty
   was computed by nothing. This runs first because the other two gates are
   asking about the quality of a provenance claim, and there is no claim here
   to assess.
2. **lineage strict equality** — the declared operator set must *equal* the
   engine-resolved set. Strict equality catches forgery (declaring what did
   not run) and omission (hiding what did) with one comparison, and the two
   sets are produced independently — one by the producer, one by the engine
   that ran them — which is what makes the comparison worth making.
3. **TTL bounds** — ``now < expires_at <= now + MAX_TTL``, with MAX_TTL
   resolved from the Control Plane at gate time (D-IMPL-39). The lower bound
   is strict: a product expiring exactly now is expired. The upper bound is
   inclusive: a product at the ceiling is at the ceiling.

**Refusal is a value, not an exception.** ``run_gates`` returns either a
:class:`ServableProduct` or a :class:`GateRefusal` subclass carrying the
failing detail. A refusal returned as data cannot be swallowed by a bare
``except``, and the caller cannot accidentally proceed — there is no product
in its hands to proceed with.

**Enforcement of "only path" mirrors single-writer.** :class:`ServableProduct`
takes a token this module alone can produce. The honest claim is DESIGN.md
§9's: no unforced path exists, and every forced path fails at construction —
never absolute prevention.

``now`` is an argument. Nothing here reads a clock: a gate whose verdict
depended on wall-clock time at replay would make replay non-deterministic
precisely at the boundary where determinism matters most.

This module holds no TTL values and no thresholds (CLAUDE.md §11, CINV-01).
Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from ccf.contracts.base import CCFContract
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    RegisteredProductClass,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "EmptyOperatorRefusal",
    "GateBypassError",
    "GateRefusal",
    "LineageMismatchRefusal",
    "ServableProduct",
    "TTLRefusal",
    "run_gates",
]

GATE_EMPTY_OPERATOR = "empty-operator-guard"
GATE_LINEAGE_EQUALITY = "lineage-strict-equality"
GATE_TTL_BOUNDS = "ttl-bounds"


class GateBypassError(TypeError):
    """A servable product was constructed outside the gate sequence."""


class GateRefusal(CCFContract):
    """Base of the structured refusals the gates return.

    Attributes:
        gate: Which gate refused.
        detail: Human-readable statement of what was wrong. The typed subclass
            fields carry the machine-readable version — the text is for the
            operator reading a log, not for a caller to parse.
    """

    gate: str
    detail: str


class EmptyOperatorRefusal(GateRefusal):
    """Gate 1: ``operators_invoked`` was empty (INV-CH7-46)."""


class LineageMismatchRefusal(GateRefusal):
    """Gate 2: declared and engine-resolved operator sets differ.

    Both sets are carried so the caller can see *which* direction failed —
    forgery, omission, or drift — without re-deriving either.
    """

    declared: frozenset[str]
    resolved: frozenset[str]


class TTLRefusal(GateRefusal):
    """Gate 3: ``expires_at`` fell outside ``(now, now + MAX_TTL]``."""

    expires_at: datetime
    now: datetime
    max_ttl_seconds: int


_GATE_TOKEN = object()


class ServableProduct:
    """A product that passed all three gates — the only servable form.

    Not constructible outside this module: :meth:`__init__` requires the
    module-private gate token. Holding one of these *is* the evidence that the
    gates ran, which is why the delivery path takes this type and not a bare
    :class:`~ccf.products.contract.ContextProductContract`.
    """

    def __init__(self, product: ContextProductContract, token: object) -> None:
        if token is not _GATE_TOKEN:
            raise GateBypassError(
                "ServableProduct is constructed only by "
                "ccf.products.gates.run_gates; the three validation gates are "
                "the only construction path of a servable product "
                "(whitepaper §7.6, INV-CH7-52)"
            )
        self._product = product

    @property
    def product(self) -> ContextProductContract:
        """The validated contract, ready for delivery."""
        return self._product


def run_gates(
    candidate: ContextProductContract,
    *,
    engine_resolved: frozenset[str],
    now: datetime,
    registry: ControlPlaneProtocol,
    product_class: RegisteredProductClass,
) -> ServableProduct | GateRefusal:
    """Run the canonical gate sequence over ``candidate``.

    Args:
        candidate: The product as the producer declares it.
        engine_resolved: The operator set the projection engine observed
            itself running.
        now: The evaluation instant, supplied by the caller.
        registry: Control Plane the MAX_TTL is resolved from.
        product_class: The registered class, carrying the pinned MAX_TTL
            reference established at registration (D-IMPL-39).

    Returns:
        A :class:`ServableProduct` when every gate passes, otherwise the
        refusal of the *first* gate that did not.

    Raises:
        ccf.controlplane.registry.ControlPlaneMissing: the pinned MAX_TTL has
            disappeared from the Control Plane since registration. Raised
            rather than refused: that is a broken deployment, not a bad
            product, and the two must not be reported the same way.
        TypeError: the pinned MAX_TTL artifact is not a
            :class:`~ccf.products.contract.MaxTTL`.
    """
    declared = candidate.lineage.operators_invoked

    if not declared:
        return EmptyOperatorRefusal(
            gate=GATE_EMPTY_OPERATOR,
            detail=(
                f"product {candidate.schema_name!r} declares no operators; a "
                "product computed by nothing is not servable (INV-CH7-46)"
            ),
        )

    if declared != engine_resolved:
        return LineageMismatchRefusal(
            gate=GATE_LINEAGE_EQUALITY,
            detail=(
                f"product {candidate.schema_name!r} declares operators "
                f"{sorted(declared)} but the engine resolved "
                f"{sorted(engine_resolved)}; lineage equality is strict in "
                "both directions (INV-CH7-47)"
            ),
            declared=declared,
            resolved=engine_resolved,
        )

    artifact = registry.resolve(
        product_class.max_ttl_key, product_class.max_ttl_version
    )
    if not isinstance(artifact, MaxTTL):
        raise TypeError(
            f"MAX_TTL at ({product_class.max_ttl_key!r}, "
            f"{product_class.max_ttl_version!r}) holds "
            f"{type(artifact).__name__}, not MaxTTL"
        )
    ceiling = now + timedelta(seconds=artifact.seconds)
    if not (now < candidate.expires_at <= ceiling):
        return TTLRefusal(
            gate=GATE_TTL_BOUNDS,
            detail=(
                f"expires_at {candidate.expires_at.isoformat()} is outside "
                f"(now, now + MAX_TTL] = ({now.isoformat()}, "
                f"{ceiling.isoformat()}] (INV-CH7-48)"
            ),
            expires_at=candidate.expires_at,
            now=now,
            max_ttl_seconds=artifact.seconds,
        )

    return ServableProduct(candidate, _GATE_TOKEN)
