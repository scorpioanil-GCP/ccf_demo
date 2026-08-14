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
   engine-resolved set. What one comparison establishes is **assembly-path
   integrity**: the declared side is the claim the producer transcribed into
   the Contract, the resolved side is the engine's record of executing the
   plan, and the gate holds a served product to the path the deployment said
   assembled it. It is not a check on whether that claim was right to begin
   with. The engine is a faithful *transcriber* of the plan rather than an
   independent witness of it —
   :meth:`~ccf.projection.engine.ProjectionEngine.execute` builds
   ``operators_invoked`` and ``steps`` in one loop over the same operator
   plan, so it has no return path where invoked ≠ planned (``D-IMPL-86``,
   Dave, 2026-08-05; CLAUDE.md §11 requires an SDK extension to cite this
   project's own decision record rather than the whitepaper). The
   forgery-and-omission reading therefore holds only in the form that
   mechanism supports: what fails here is a declaration that does not match
   the assembly path — something reshaped, re-serialized, or transcribed
   wrongly between the plan and the Contract — and **not** a producer
   misdeclaring its own requirements. That drift is authorable, and it fails
   *upstream* at
   :func:`~ccf.deployment.binder.refuse_operator_set_divergence`, which
   compares two separately authored Control Plane artifacts before there is
   a product to gate (design E2).
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

**The additive source-attestation gate (Phase 15.2, D-09).** SDK-defined per
CLAUDE.md §11: after the canonical three, :func:`run_gates` additionally
refuses a candidate whose **pinned source attestation** reports a mode
outside the product class's accepted-mode sets — an unordered per-dimension
comparison (no strength ordering between modes is invented), with the
refusal naming the failing dimension. The pinned attestation arrives as a
keyword-only argument because the candidate contract cannot carry it (a
product does not attest its own source; the engine's execution record does),
and ``None`` — a record produced before attestation existed, or a bypassing
caller against a pre-phase reader — passes: the compatibility posture. The
canonical three gates, their order, and their refusal precedence are
byte-untouched.

This module holds no TTL values and no thresholds (CLAUDE.md §11, CINV-01).
Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal, Never

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.graph.protocols import SourceAttestation
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
    "GATE_SOURCE_ATTESTATION",
    "GATE_TTL_BOUNDS",
    "PYDANTIC_MODEL_FORMS",
    "AttestationRefusal",
    "EmptyOperatorRefusal",
    "GateBypassError",
    "GateRefusal",
    "LineageAttributionRefusal",
    "LineageMismatchRefusal",
    "ServableProduct",
    "ServableProductNotAModel",
    "TTLRefusal",
    "refuse_attestation",
    "run_federated_gates",
    "run_gates",
]

GATE_EMPTY_OPERATOR = "empty-operator-guard"
GATE_LINEAGE_EQUALITY = "lineage-strict-equality"
GATE_LINEAGE_ATTRIBUTABILITY = "lineage-attributability"
GATE_TTL_BOUNDS = "ttl-bounds"
GATE_SOURCE_ATTESTATION = "source-attestation"


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


class AttestationRefusal(GateRefusal):
    """The additive gate: the source's attestation mode is not accepted (D-09).

    SDK-defined per CLAUDE.md §11, deriving from :class:`GateRefusal` rather
    than paralleling it for the reason
    :class:`~ccf.peering.admission.AdmissionRefusal` records: a source meets
    the fabric's one gate discipline, not a second one that happens to look
    similar. The ``ServableProduct | GateRefusal`` return union of
    :func:`run_gates` is therefore unchanged by this refusal existing.

    Both sides of the comparison are carried — the
    ``PayloadTooLargeRefusal`` diagnostic-pair style — so the refusal names
    the failing dimension per D-09 and a caller never re-derives either side
    to learn what the gap was.

    Attributes:
        failing_dimension: Which attestation dimension refused. Exactly one
            is named — the first that failed, in the fixed
            ``policy_binding``-then-``lineage`` order — because "below
            accepted modes" is a per-dimension fact, not an aggregate.
        source_mode: The mode the source declared on that dimension.
        accepted_modes: The product class's accepted-mode set for that
            dimension — an unordered set (D-09's "minima" realized as
            accepted-mode sets; no strength ordering exists between modes).
    """

    failing_dimension: Literal["policy_binding", "lineage"]
    source_mode: str
    accepted_modes: frozenset[str]


def refuse_attestation(
    *,
    attestation: SourceAttestation | None,
    product_class: RegisteredProductClass,
) -> AttestationRefusal | None:
    """The one D-09 accepted-modes comparison — shared by both layers.

    Called by :meth:`ccf.projection.engine.ProjectionEngine.check_source_attestation`
    (the caller-visible pre-execute check) and by :func:`run_gates` (the
    structural gate-path enforcement), so the two layers cannot drift into
    two readings of "accepted". Pure over its arguments: no I/O, no clock,
    no query.

    ``None`` passes, and the pass is deliberate — the compatibility posture:
    an attestation pinned as ``None`` is a record produced before source
    attestation existed, or an execution driven by a bypassing caller
    against a pre-phase reader that never reported one. Refusing it would
    reclassify every pre-phase decision as below-modes retroactively;
    admitting it leaves the audit trail (the unconditional dimension-1 pin)
    to say exactly what was and was not attested.

    Returns:
        ``None`` when every attested dimension's mode is in the class's
        accepted set, otherwise the :class:`AttestationRefusal` naming the
        first failing dimension (``policy_binding`` checked before
        ``lineage``, a fixed order so the named dimension is deterministic).
    """
    if attestation is None:
        return None
    if attestation.policy_binding not in product_class.accepted_policy_binding_modes:
        return AttestationRefusal(
            gate=GATE_SOURCE_ATTESTATION,
            detail=(
                f"source attests policy_binding={attestation.policy_binding!r} "
                f"but class {product_class.schema_name!r} accepts "
                f"{sorted(product_class.accepted_policy_binding_modes)}; the "
                "accepted-mode sets are unordered — the source's mode must be "
                "a member (D-09)"
            ),
            failing_dimension="policy_binding",
            source_mode=attestation.policy_binding,
            accepted_modes=frozenset(product_class.accepted_policy_binding_modes),
        )
    if attestation.lineage not in product_class.accepted_lineage_modes:
        return AttestationRefusal(
            gate=GATE_SOURCE_ATTESTATION,
            detail=(
                f"source attests lineage={attestation.lineage!r} but class "
                f"{product_class.schema_name!r} accepts "
                f"{sorted(product_class.accepted_lineage_modes)}; the "
                "accepted-mode sets are unordered — the source's mode must be "
                "a member (D-09)"
            ),
            failing_dimension="lineage",
            source_mode=attestation.lineage,
            accepted_modes=frozenset(product_class.accepted_lineage_modes),
        )
    return None


_GATE_TOKEN = object()


#: Every pydantic model spelling :class:`ServableProduct` deliberately does not
#: have — enumerated **once**, exhaustively, rather than discovered one instance
#: at a time (the ``CONTAINER_FORMS`` precedent from Phase 15.6's
#: ``tests/invariants/test_no_obligation_vocabulary.py``).
#:
#: Both v1 and v2 spellings, and both the construction and the dump halves: a
#: reader who has just been handed one of these reaches for ``model_dump`` as
#: readily as for ``model_copy``, and a v1-era reader reaches for ``parse_obj``.
#: Closing them on different days would leave the papercut open at whichever
#: spelling was not thought of.
#:
#: Public rather than private because it is the machine-readable statement of
#: what this type is not, and because a test that parametrizes over it is
#: non-vacuous in a way a hand-listed test is not. Adding a spelling here adds
#: the refusal on both channels at once (D-IMPL-126 item (2)).
PYDANTIC_MODEL_FORMS = frozenset(
    {
        "construct",
        "from_orm",
        "model_construct",
        "model_copy",
        "model_dump",
        "model_dump_json",
        "model_json_schema",
        "model_validate",
        "model_validate_json",
        "model_validate_strings",
        "parse_file",
        "parse_obj",
        "parse_raw",
    }
)


class ServableProductNotAModel(GateBypassError, AttributeError):
    """A pydantic spelling was reached for on a type that is not a model.

    SDK-defined per CLAUDE.md §11 (``D-IMPL-126`` item (2)). It exists for its
    **inheritance**, which is the whole of its reason:

    * ``GateBypassError`` — so a caller already writing
      ``except GateBypassError`` around the gate path catches this too, and so
      the refusal reads as what it is: a report about the gate discipline, not
      a report about pydantic.
    * ``AttributeError`` — because ``GateBypassError`` subclasses ``TypeError``
      and nothing else, so a refusal deriving from it alone would make
      ``hasattr(ServableProduct, "model_construct")`` **raise** instead of
      returning ``False``, and ``getattr(servable, "model_copy", None)`` raise
      instead of defaulting. A duck-type probe must degrade rather than
      explode; that hazard is created by this fix, so it is closed by it.
    """


def _not_a_model(owner: str, name: str) -> ServableProductNotAModel:
    """The one refusal message, three statements in a fixed order.

    Deliberately one message for both channels and for both halves of
    :data:`PYDANTIC_MODEL_FORMS`: what a reader needs to learn is the same
    whichever spelling they reached for and whichever channel they reached it
    on — that this type is not a pydantic model, that the gate sequence is the
    only way to hold one, and that the validated contract they actually want is
    one attribute away.
    """
    return ServableProductNotAModel(
        f"{owner}.{name} does not exist: ServableProduct is not a pydantic "
        "model and is deliberately unconstructible. The only construction "
        "path is ccf.products.gates.run_gates, because holding a "
        "ServableProduct *is* the evidence that the three validation gates "
        "ran. This is INV-CH7-52 (whitepaper §7.6) working as specified, not "
        "a pydantic version problem. The validated contract is at "
        "`.product` — that one *is* a pydantic model, so "
        f"`servable.product.{name}` is very likely what you meant."
    )


class _ServableProductMeta(type):
    """The **class** channel of the refusal — and only that channel.

    ``ServableProduct.model_construct(...)`` is a lookup on the class, so it
    misses the class and its bases and lands on the metaclass. Measured: a
    metaclass ``__getattr__`` covers this channel and leaves the instance
    channel bare, which is why :meth:`ServableProduct.__getattr__` exists
    alongside it reading the same frozenset.

    This adds no construction path. Attribute *lookup* only: ``__call__`` is
    not overridden and :meth:`ServableProduct.__init__`'s gate-token check is
    untouched.
    """

    def __getattr__(cls, name: str) -> Never:
        if name in PYDANTIC_MODEL_FORMS:
            raise _not_a_model(cls.__name__, name)
        # Outside the enumerated set the default behaviour is restored
        # verbatim. The scoping is the point: a refusal that swallowed a typo
        # would replace one confusing error with a more confident one.
        raise AttributeError(
            f"type object {cls.__name__!r} has no attribute {name!r}"
        )


class ServableProduct(metaclass=_ServableProductMeta):
    """A product that passed all three gates — the only servable form.

    Not constructible outside this module: :meth:`__init__` requires the
    module-private gate token. Holding one of these *is* the evidence that the
    gates ran, which is why the delivery path takes this type and not a bare
    :class:`~ccf.products.contract.ContextProductContract`.

    **It is not a pydantic model, and it now says so** (``D-IMPL-126`` item
    (2)). Every spelling in :data:`PYDANTIC_MODEL_FORMS` is refused with a
    message naming ``run_gates`` and INV-CH7-52, on *both* attribute channels —
    the class, through :class:`_ServableProductMeta`, and the instance, through
    :meth:`__getattr__` below. Any other name still raises a plain
    ``AttributeError``.
    """

    def __getattr__(self, name: str) -> Never:
        """The **instance** channel — the one a reader is most likely to hit.

        A metaclass ``__getattr__`` does not run for instance attribute lookup,
        and ``model_copy``, ``model_dump`` and ``parse_obj`` are *instance*
        methods in pydantic: they are exactly what someone holding a returned
        object reaches for. Without this the fix would cover only the channel a
        reader is least likely to use.

        Runs only on a miss, so ``.product`` and ``._product`` resolve normally
        and nothing about the type's real surface changes.
        """
        if name in PYDANTIC_MODEL_FORMS:
            raise _not_a_model(type(self).__name__, name)
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}"
        )

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
    source_attestation: SourceAttestation | None = None,
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
            As of Phase 15.2 it also carries the D-09 accepted attestation
            modes the additive gate below compares against.
        source_attestation: The **pinned** source attestation of the
            execution that produced ``candidate`` — the governed path passes
            ``execution.source_attestation``, the value the engine observed
            at the read seam and threads into replay dimension 1. A
            keyword-only argument with a ``None`` default rather than a
            field on the candidate, because a product does not attest its
            own source; and ``None`` passes — the compatibility posture
            :func:`refuse_attestation` documents — so every pre-attestation
            call site is byte-for-byte unchanged in behavior. When present
            and below the class's accepted modes, the additive
            :data:`GATE_SOURCE_ATTESTATION` gate returns an
            :class:`AttestationRefusal` naming the failing dimension, and
            no :class:`ServableProduct` exists (D-09).

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

    attestation = refuse_attestation(
        attestation=source_attestation, product_class=product_class
    )
    if attestation is not None:
        return attestation

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
    within a fabric, attributable across one*. Inside one fabric
    :func:`run_gates` has something to compare a declaration against because
    the consumer's **own** engine executed the plan and recorded what it ran —
    a faithful transcription of that plan, not an independent witness of it
    (see this module's docstring). That buys assembly-path integrity and no
    more. Across a Peering the consumer ran no engine at all — the operators
    executed in another fabric, in another process — so there is not even a
    transcription on this side: the only operator set in hand is the
    declaration itself, and passing it in as its own witness would make the
    comparison trivially true. That is why this sequence does not run that
    gate at all, and the omission is **better** supported under the corrected
    reading than under the original one — the local path's justification was
    never independence, and what the federated path lacks is the
    transcription, not a witness.

    **Premise corrected, ruling undisturbed (``D-IMPL-86``, 2026-08-05).**
    This passage previously read "inside one fabric the projection engine's
    own record of what ran is an independent witness". It is not, under any
    design considered: ``operators_invoked`` and ``steps`` are built in one
    loop over the same operator plan. What that correction reaches is
    ``D-IMPL-57``'s **intra-fabric premise**, which was an assumed premise for
    the federated ruling rather than something adjudicated. The federated
    ruling stated above stands exactly as Dave made it and is not reopened
    here. Where **authorable** drift fails instead is
    :func:`~ccf.deployment.binder.refuse_operator_set_divergence`, upstream of
    every gate in either sequence.

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
