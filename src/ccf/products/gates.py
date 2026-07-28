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

**The federated form of the sequence.** :func:`run_federated_gates` is the
same sequence for a product that arrived through a Peering (``D-IMPL-59``),
with gate 2 replaced: *products admitted through a Peering are attributable;
locally assembled products are verifiable* (``D-IMPL-57``, Dave's ruling of
2026-07-27, reading (a)). Gates 1 and 3 are shared outright — one reading of
INV-CH7-46 and one pinned MAX_TTL, not two — and the local sequence above is
unchanged in behaviour, order and refusal types. See that function for what
attributability does and does not establish.

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
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    RegisteredProductClass,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "GATE_EMPTY_OPERATOR",
    "GATE_LINEAGE_ATTRIBUTABILITY",
    "GATE_LINEAGE_EQUALITY",
    "GATE_TTL_BOUNDS",
    "EmptyOperatorRefusal",
    "GateBypassError",
    "GateRefusal",
    "LineageAttributionRefusal",
    "LineageMismatchRefusal",
    "ServableProduct",
    "TTLRefusal",
    "run_federated_gates",
    "run_gates",
]

GATE_EMPTY_OPERATOR = "empty-operator-guard"
GATE_LINEAGE_EQUALITY = "lineage-strict-equality"
GATE_LINEAGE_ATTRIBUTABILITY = "lineage-attributability"
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


class LineageAttributionRefusal(GateRefusal):
    """Federated gate 2: the gated bytes are not the bytes that were signed.

    Both sides of the mismatch are carried, per this module's refusal
    discipline: the declared operator plan, the content address the peer's
    signature covered, and the content address of the candidate as gated. A
    caller reading this refusal never re-hashes anything to learn what the gap
    was (D-IMPL-57).
    """

    declared: frozenset[str]
    attested_address: str
    candidate_address: str


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

    empty = _refuse_empty_operators(candidate)
    if empty is not None:
        return empty

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

    ttl = _refuse_ttl(
        candidate, now=now, registry=registry, product_class=product_class
    )
    if ttl is not None:
        return ttl

    return ServableProduct(candidate, _GATE_TOKEN)


def run_federated_gates(
    candidate: ContextProductContract,
    *,
    attested_address: str,
    now: datetime,
    registry: ControlPlaneProtocol,
    product_class: RegisteredProductClass,
) -> ServableProduct | GateRefusal:
    """Run the federated form of the gate sequence over ``candidate``.

    **Products admitted through a Peering are attributable; locally assembled
    products are verifiable.** That is Dave's ``D-IMPL-57`` ruling of
    2026-07-27 (reading (a)) stated as a pairing: INV-CH7-47 is *verifiable
    within a fabric, attributable across one*. Inside one fabric the projection
    engine's own record of what ran is an independent witness, so
    :func:`run_gates` can compare a declaration against it. Across a Peering
    the consumer ran no engine — the operators executed in another fabric, in
    another process — and no independent witness exists on this side. Passing
    the declaration in as its own witness would make the comparison trivially
    true, which is why this sequence does not run that gate at all.

    The contract is stated at **Peering level rather than A2A level**:
    ``D-IMPL-59`` makes A2A one Peering transport rather than the concept, so
    the guarantee belongs to the seam and a second transport inherits it rather
    than restating it.

    What the attributability gate establishes is that the operator plan the
    product declares is covered by a signature from a key the peer was entitled
    to use, and is therefore **attributable and non-repudiable** — *not* that
    the plan was actually run. The accepted consequence, in the ruling's own
    words: *a compromised or buggy peer can assert an operator plan it did not
    run, and the consuming fabric will admit the product.* What the gate refuses
    is the case where the bytes in hand are not the bytes whose signature
    verified — something reshaped or re-serialized the product between
    verification and gating, at which point the declared lineage is no longer
    covered by anything the peer signed, and attribution is nil.

    The sequence, and it is an order:

    1. **empty-operator guard** — unchanged from the local path, and fully
       meaningful across a boundary: a product declaring no operators was
       computed by nothing, whoever signed it (INV-CH7-46).
    2. **attributability** — ``content_hash(candidate) == attested_address``.
    3. **TTL bounds** — the same INV-CH7-48 bound against the same pinned
       MAX_TTL a locally assembled product is held to. Expiry is a property of
       the product and the consumer's clock and needs nothing the consumer
       lacks.

    Args:
        candidate: The product as the peer declares it, parsed from the bytes
            whose signature verified.
        attested_address: The content address of those bytes — the witness the
            signature check established. Never derived from ``candidate``:
            deriving it here would reintroduce exactly the self-witnessing this
            function exists to remove.
        now: The evaluation instant, supplied by the caller.
        registry: Control Plane the MAX_TTL is resolved from.
        product_class: The registered class carrying the pinned MAX_TTL.

    Returns:
        A :class:`ServableProduct` when every gate passes, otherwise the
        refusal of the *first* gate that did not.

    Raises:
        ccf.controlplane.registry.ControlPlaneMissing: the pinned MAX_TTL has
            disappeared from the Control Plane since registration — a broken
            deployment, not a bad product.
        TypeError: the pinned MAX_TTL artifact is not a
            :class:`~ccf.products.contract.MaxTTL`.
    """
    empty = _refuse_empty_operators(candidate)
    if empty is not None:
        return empty

    candidate_address = content_hash(candidate)
    if candidate_address != attested_address:
        return LineageAttributionRefusal(
            gate=GATE_LINEAGE_ATTRIBUTABILITY,
            detail=(
                f"product {candidate.schema_name!r} as gated hashes to "
                f"{candidate_address} but the verified signature covered "
                f"{attested_address}; the declared operator plan "
                f"{sorted(candidate.lineage.operators_invoked)} is therefore "
                "not attributable to the peer (D-IMPL-57)"
            ),
            declared=candidate.lineage.operators_invoked,
            attested_address=attested_address,
            candidate_address=candidate_address,
        )

    ttl = _refuse_ttl(
        candidate, now=now, registry=registry, product_class=product_class
    )
    if ttl is not None:
        return ttl

    return ServableProduct(candidate, _GATE_TOKEN)


def _refuse_empty_operators(
    candidate: ContextProductContract,
) -> EmptyOperatorRefusal | None:
    """Gate 1, shared by both sequences: a product computed by nothing.

    Factored rather than duplicated so the two sequences cannot drift into two
    readings of INV-CH7-46.
    """
    if candidate.lineage.operators_invoked:
        return None
    return EmptyOperatorRefusal(
        gate=GATE_EMPTY_OPERATOR,
        detail=(
            f"product {candidate.schema_name!r} declares no operators; a "
            "product computed by nothing is not servable (INV-CH7-46)"
        ),
    )


def _refuse_ttl(
    candidate: ContextProductContract,
    *,
    now: datetime,
    registry: ControlPlaneProtocol,
    product_class: RegisteredProductClass,
) -> TTLRefusal | None:
    """Gate 3, shared by both sequences, including its MAX_TTL resolution.

    Shared for the reason the A2A admission gate calls into this module at all:
    a federated product must age under the *same* pinned ceiling a local one
    does, and a second copy of this bound is a second place for it to differ.
    """
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
    if now < candidate.expires_at <= ceiling:
        return None
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
