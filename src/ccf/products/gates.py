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

**What ``lineage-attributability`` is, and is not (ledger row ``24.5-L-27``).**
:data:`GATE_LINEAGE_ATTRIBUTABILITY` names the A2A attestation gate and
nothing else: a product admitted through a Peering is attributable when
``content_hash(candidate) == attested_address`` — the gated bytes are the
bytes whose signature verified — and the operator plan it declares is
therefore the one the peer attested (``D-IMPL-57``). It is **not** a
per-attribute lineage obligation; it says nothing about whether each derived
line of a product names the inputs it was computed from. ``CP-SPEC-003``
§F.4 #3 read the name that way and recorded a naming finding. The
per-derived-line ``inputs`` that cp-03 carries is a *product* gate today
(``OFS-G12``), and the SDK's own declared form of that obligation is ledger
row ``24.5-L-26`` — owned there, not by this token. This paragraph is a
bounded correction (``D-07.1``): the token string, the refusal class and the
runner's signature are unchanged.

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

**The declared-obligations gate (Phase 24.5 Wave 2, ``D-IMPL-237``).** The
ONE structural serve-time gate mechanism the SDK ships beyond the five tokens
``D-IMPL-238`` records: after every universal gate above has passed, both
runners hold the candidate to what its product class *declared* in
:class:`~ccf.products.contract.ServeObligations` — a ``D_c`` ceiling
(ledger row ``24.5-L-14``; whitepaper §7.7.4–§7.7.8, where Context Debt gates
Forced LLM and Fail-Closed behavior) and a per-attribute lineage obligation
(ledger row ``24.5-L-26``). It runs LAST because it is the only *declared*
gate: every universal gate precedes it, and a class that declares nothing
(:data:`~ccf.products.contract.NO_SERVE_OBLIGATIONS`) never reaches a
comparison. The ceiling is class-declared and a request may only TIGHTEN it
(``D-IMPL-240`` (3); the fold that establishes it moved to
:mod:`ccf.products.constraints` in ``24.6-03``, so what arrives here is an
already-resolved value with its authority recorded); the lineage half reads
the presence and non-emptiness of a NAMED payload member and nothing else —
it is a structural gate, never a payload gate (``D-IMPL-238`` reading
``D-IMPL-102`` limb 3). ``_GATE_TOKEN``, :class:`_ServableProductMeta` and
:class:`GateBypassError` are untouched by it: the new step returns a refusal
before the token is minted, exactly as the four before it do.

**The empty-operator gate's two halves, by name (Phase 24.5 Wave 2, ledger
row ``24.5-L-24``; ``D-IMPL-238`` second sentence).** Two assertions shared
the name ``empty-operator-guard``: the SDK's — a product that DECLARED no
operators (INV-CH7-46) — and the Standard's — an operator that RETURNED an
empty set, which nothing in ``src/`` said anything about while cp-00's
``IH-G07`` and cp-01's ``CPR-G08`` carried it as product gates. They are now
two named structural gates, adjacent in both runners with the declared half
first: :data:`GATE_EMPTY_OPERATOR` (:func:`_refuse_empty_operators`,
unchanged) and :data:`GATE_EMPTY_OPERATOR_RESULT`
(:func:`_refuse_empty_results`, :class:`EmptyResultRefusal`). The returned
half reads the engine's own record,
:attr:`~ccf.projection.engine.ExecutionResult.empty_results`, threaded as a
keyword-only ``empty_results`` whose ``None`` default is *not observed* and
passes — the same compatibility posture as ``source_attestation``, so every
pre-phase call site is byte-identical. It is not a second mechanism and not
a payload gate: it reads operator keys, never the payload (limb 3).

This module holds no TTL values and no thresholds (CLAUDE.md §11, CINV-01):
the ceiling's number is the deployment's, authored on the product class.
Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Sized
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Final, Literal, Never

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
    "DEBT_TOLERANCE_PARAMETER",
    "GATE_DECLARED_OBLIGATIONS",
    "GATE_EMPTY_OPERATOR",
    "GATE_EMPTY_OPERATOR_RESULT",
    "GATE_LINEAGE_ATTRIBUTABILITY",
    "GATE_LINEAGE_EQUALITY",
    "GATE_SOURCE_ATTESTATION",
    "GATE_TTL_BOUNDS",
    "PYDANTIC_MODEL_FORMS",
    "AttestationRefusal",
    "DeclaredObligationRefusal",
    "EmptyOperatorRefusal",
    "EmptyResultRefusal",
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
# The empty-operator gate's two halves, separated by NAME (24.5-L-24;
# D-IMPL-238 second sentence). ``empty-operator-guard`` is the SDK's half: a
# product DECLARING no operators (INV-CH7-46, unchanged).
# ``empty-operator-result`` is the Standard's half: an operator RETURNING an
# empty set. Two tokens so a refusal names which half fired; neither is a
# second mechanism — both are structural, both read the execution record and
# never the payload (limb 3).
GATE_EMPTY_OPERATOR_RESULT = "empty-operator-result"
GATE_LINEAGE_EQUALITY = "lineage-strict-equality"
GATE_LINEAGE_ATTRIBUTABILITY = "lineage-attributability"
GATE_TTL_BOUNDS = "ttl-bounds"
GATE_SOURCE_ATTESTATION = "source-attestation"
# The ONE structural mechanism D-IMPL-237 licenses beyond the five tokens
# above, which D-IMPL-238 records by name as the membership it joins
# (24.5-L-14, 24.5-L-26). Not a payload gate (limb 3), not a second mechanism.
GATE_DECLARED_OBLIGATIONS = "declared-obligations"

#: The Standard's universal request parameter (``references/
#: Context_Product_Specification_Standard_v0-3.md`` §2.4) by which a caller
#: may TIGHTEN — never loosen — the ceiling its product class declared
#: (``D-IMPL-240`` (3), ``24.5-L-14``). The resolver reads it off
#: ``request.parameters`` only when the class declares a ceiling and the
#: request contract declares the parameter; otherwise
#: :func:`~ccf.products.request.refuse_request` has already refused it as
#: undeclared, and an undeclared class ignores it whatever it says. That same
#: boundary refuses a declared, well-typed number outside ``[0, 1]`` by name
#: (``not-a-proportion``; ``24.5-REVIEW.md`` WR-02, Dave, 2026-09-02), so what
#: reaches the resolution through the governed resolver is always a proportion
#: — a request states a tighter ceiling or none, never a number that is not a
#: ceiling at all.
#:
#: CINV-01, reasoned rather than assumed: this is a parameter NAME the SDK
#: owns as mechanism vocabulary — on the footing of the four request axes
#: (subject, instant, perspective, tier), which are names the SDK also owns —
#: and never a value. No number, no threshold and no default tolerance lives
#: here or anywhere in ``src/``; the ceiling's number is authored on the
#: product class by the deployment, and the request's number is the caller's.
DEBT_TOLERANCE_PARAMETER: Final[str] = "debt_tolerance"


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


class EmptyResultRefusal(GateRefusal):
    """Gate 1's second half: an operator RETURNED an empty set (``24.5-L-24``).

    SDK-defined per CLAUDE.md §11, beside the whitepaper's INV-CH7-46 half
    (:class:`EmptyOperatorRefusal`) and distinguishable from it by name — the
    ``gate`` token is :data:`GATE_EMPTY_OPERATOR_RESULT`, never
    :data:`GATE_EMPTY_OPERATOR`. The Standard's sentence for this half is the
    one cp-00's ``IH-G07`` and cp-01's ``CPR-G08`` carried as product gates
    before the SDK named it: *an empty assembled set fails closed*.

    What it carries follows the module's refusal discipline — both what the
    caller needs to branch on and everything the gate observed:

    Attributes:
        operator_key: The FIRST operator, in sorted key order, whose output
            view carried zero entities and zero relationships. One name for a
            consumer that branches on a key.
        empty_operators: Every such operator key, so a plan in which two
            operators returned empty is reported once, whole, and a reader
            never re-derives the rest from ``detail``.

    Observed from :attr:`~ccf.projection.engine.ExecutionResult.empty_results`,
    the engine's own record — never from the payload (``D-IMPL-238`` limb 3).
    """

    operator_key: str
    empty_operators: frozenset[str]


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

    What this refusal is, and is not (ledger row ``24.5-L-27``): it is the
    A2A attestation gate's refusal — ``content_hash(candidate)`` did not equal
    ``attested_address``, so the declared operator plan is not attributable
    to the peer (``D-IMPL-57``). It is *not* a per-attribute lineage refusal.
    This module carries no per-attribute lineage obligation; the one the SDK
    declares is ledger row ``24.5-L-26``. Bounded correction (``D-07.1``): no
    field, name or gate token moves.
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


class DeclaredObligationRefusal(GateRefusal):
    """The declared-obligations gate: the product broke what its class declared.

    SDK-defined per CLAUDE.md §11 — whitepaper §7.6 (the validation gates)
    and §7.7.4–§7.7.8 (Context Debt as the quantified shortfall that gates
    Forced LLM and Fail-Closed behavior). The ONE structural mechanism
    ``D-IMPL-237`` licenses, carrying both of the obligations it enforces
    (ledger rows ``24.5-L-14`` and ``24.5-L-26``) under one token,
    :data:`GATE_DECLARED_OBLIGATIONS`, so that there is one gate and not two.
    Derives from :class:`GateRefusal` for the reason :class:`AttestationRefusal`
    records: a product meets the fabric's one gate discipline, and the
    ``ServableProduct | GateRefusal`` return union of :func:`run_gates` is
    unchanged by this refusal existing. The HTTP door maps this kind to the
    Standard's ``409`` (*"Debt gate exceeded → 409 with the debt block"*,
    §9); this module knows nothing of status codes.

    Both sides are carried, in the :class:`TTLRefusal` voice: a caller never
    re-derives either to learn what the gap was.

    Attributes:
        obligation: Which declared obligation refused — ``debt-ceiling`` (the
            candidate's ``D_c`` exceeded the effective ceiling, or the class
            declared a ceiling and the candidate carries no assessment) or
            ``lineage-inputs`` (a named payload member the class obliges is
            absent or empty). Two SDK code paths under one gate, never a
            deployment vocabulary.
        declared: What the class declared, rendered: the effective ceiling as
            a decimal string, or the obliged member's name.
        observed: What the candidate carried, rendered: its ``D_c`` as a
            decimal string, ``no-assessment``, ``absent`` or ``empty``.
    """

    obligation: Literal["debt-ceiling", "lineage-inputs"]
    declared: str
    observed: str


def _refuse_declared_obligations(
    candidate: ContextProductContract,
    *,
    product_class: RegisteredProductClass,
    debt_tolerance: Decimal | None,
) -> DeclaredObligationRefusal | None:
    """The declared-obligations gate, shared by both sequences — one function, two obligations.

    Factored rather than duplicated for the reason gates 1 and 3 are: the two
    runners cannot drift into two readings of what a class declared.

    **The debt half** (``24.5-L-14``, and an INTERIM as of ``24.6-03``).
    ``debt_tolerance`` is now the tolerance the Authority layer **resolved**
    upstream — the caller's value, or the policy's where a constraint bounded
    it, with the authority that set it recorded (``D-IMPL-254``) — rather than
    a raw request parameter this gate folds for the first time. What has not
    moved is that the class's own ceiling is the floor of strictness: a
    resolved tolerance may tighten it and never loosen it, which is why the
    ``min`` is inlined above rather than deleted along with
    ``24.5-L-14``'s helper. ``24.6-04`` retires this half entirely, at which
    point the class's ceiling becomes an authority in the resolution and there
    is one fold rather than two. ``None`` — the class declares no ceiling and
    nothing resolved a tolerance — is silent. Under a ceiling, a candidate carrying no assessment is refused
    (``observed="no-assessment"``): a class that declares a ceiling cannot be
    served unmeasured, since an unmeasured product is neither within nor
    over it. A candidate whose ``D_c`` exceeds the ceiling is refused with
    both numbers. No principal and no perspective reach this comparison
    (``D-IMPL-105``): ``D_c`` is entitlement-neutral, as it was assessed.

    **The lineage half** (``24.5-L-26``). For each member the class names in
    ``lineage_inputs_at``, in sorted order so the named member is
    deterministic: absent or ``None`` → ``observed="absent"``; a sized value
    of length zero → ``observed="empty"``. Nothing else about the payload is
    read — presence and non-emptiness of a NAMED top-level member only. That
    is what keeps this a structural gate under ``D-IMPL-238``'s reading of
    ``D-IMPL-102`` limb 3: a payload whose named member holds anything at all
    serves, and no shape, type or schema is consulted.

    Returns:
        ``None`` when every declared obligation holds, otherwise the refusal
        naming the first that did not — the debt half before the lineage
        half, a fixed order.
    """
    obligations = product_class.serve_obligations
    # INTERIM — 24.6-04 retires this half. The fold that used to live in
    # 24.5-L-14's helper is inlined here, unchanged in behavior, rather than
    # deleted with it: the class's ceiling is the FLOOR OF STRICTNESS
    # (`D-IMPL-240` (3), threat `T-24.5-33`), and dropping that during the one
    # wave between the resolver rewrite and the tolerance step would let a
    # caller LOOSEN a ceiling its class declared.
    # Both limbs are the deleted helper's, verbatim in behavior: an undeclared
    # class is unaffected whatever the request says (a request cannot CREATE a
    # ceiling, because a ceiling is class governance and a caller is not the
    # class), and a declared one is tightened and never loosened.
    ceiling = obligations.debt_ceiling
    if ceiling is not None and debt_tolerance is not None:
        ceiling = min(ceiling, debt_tolerance)
    if ceiling is not None:
        if candidate.debt is None:
            return DeclaredObligationRefusal(
                gate=GATE_DECLARED_OBLIGATIONS,
                detail=(
                    f"product {candidate.schema_name!r} carries no debt "
                    f"assessment but its class declares a D_c ceiling of "
                    f"{ceiling}; a class that declares a ceiling cannot be "
                    "served unmeasured — debt gate exceeded, 409 with the debt "
                    "block (Standard §9; 24.5-L-14)"
                ),
                obligation="debt-ceiling",
                declared=str(ceiling),
                observed="no-assessment",
            )
        if candidate.debt.debt > ceiling:
            return DeclaredObligationRefusal(
                gate=GATE_DECLARED_OBLIGATIONS,
                detail=(
                    f"product {candidate.schema_name!r} carries D_c "
                    f"{candidate.debt.debt}, over the effective ceiling "
                    f"{ceiling} its class declared (a request may tighten "
                    "that ceiling, never loosen it — D-IMPL-240 (3)); debt "
                    "gate exceeded, 409 with the debt block (Standard §9; "
                    "whitepaper §7.7.4–§7.7.8; 24.5-L-14)"
                ),
                obligation="debt-ceiling",
                declared=str(ceiling),
                observed=str(candidate.debt.debt),
            )
    for member in sorted(obligations.lineage_inputs_at):
        value = candidate.payload.get(member)
        if value is None:
            observed = "absent"
        elif isinstance(value, Sized) and len(value) == 0:
            observed = "empty"
        else:
            continue
        return DeclaredObligationRefusal(
            gate=GATE_DECLARED_OBLIGATIONS,
            detail=(
                f"product {candidate.schema_name!r} declares a lineage "
                f"obligation on payload member {member!r}, which is "
                f"{observed}; every served line must name what it was "
                "computed from (24.5-L-26)"
            ),
            obligation="lineage-inputs",
            declared=member,
            observed=observed,
        )
    return None


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
    debt_tolerance: Decimal | None = None,
    empty_results: frozenset[str] | None = None,
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
        debt_tolerance: The **effective** tolerance this product is held to
            (``24.5-L-14``, ``D-IMPL-240`` (3); resolved upstream as of
            ``24.6-03``). It is the value the Authority layer resolved from the
            class's declaration, the caller's request and the policy
            constraints in force — a value with a recorded authority behind it
            rather than a number this gate folds. ``None`` — the default, and
            every pre-phase call site — means *the class's ceiling stands*; and
            a class that declares no ceiling is unaffected whatever is passed.
            INTERIM: ``24.6-04`` retires the debt half of this gate.
        empty_results: The operator keys whose output view carried zero
            entities and zero relationships, as the engine observed them
            (``24.5-L-24``; :attr:`~ccf.projection.engine.ExecutionResult.empty_results`).
            The governed resolver passes ``execution.empty_results``.
            ``None`` — the default, and every pre-phase call site — means
            *not observed* and passes, on the ``source_attestation``
            compatibility posture; the empty set is the engine's positive
            *no operator returned empty* and passes too. A non-empty set is
            refused by name (:data:`GATE_EMPTY_OPERATOR_RESULT`).

    Returns:
        A :class:`ServableProduct` when every gate passes, otherwise the
        refusal of the *first* gate that did not. The order is: the
        empty-operator gate's two halves, adjacent and declared half first
        (``empty-operator-guard``, then ``empty-operator-result`` —
        ``24.5-L-24``), lineage strict equality, TTL bounds, source
        attestation, then — LAST, because every universal gate precedes a
        declared one — the :data:`GATE_DECLARED_OBLIGATIONS` step, which is
        silent for a class that declares nothing (``D-IMPL-237``).

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

    returned_empty = _refuse_empty_results(candidate, empty_results=empty_results)
    if returned_empty is not None:
        return returned_empty

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

    obligation = _refuse_declared_obligations(
        candidate, product_class=product_class, debt_tolerance=debt_tolerance
    )
    if obligation is not None:
        return obligation

    return ServableProduct(candidate, _GATE_TOKEN)


def run_federated_gates(
    candidate: ContextProductContract,
    *,
    attested_address: str,
    now: datetime,
    registry: ControlPlaneProtocol,
    product_class: RegisteredProductClass,
    debt_tolerance: Decimal | None = None,
    empty_results: frozenset[str] | None = None,
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

    **The name, read plainly (ledger row ``24.5-L-27``).**
    ``lineage-attributability`` IS that comparison —
    ``content_hash(candidate) == attested_address``, the A2A attestation gate
    of ``D-IMPL-57`` — and nothing more. It is NOT a per-attribute lineage
    obligation: it does not ask whether each derived line of a product names
    the inputs it was computed from. ``CP-SPEC-003`` §F.4 #3 read the name as
    the latter and recorded a naming finding; that obligation is carried
    today by cp-03's product gate ``OFS-G12``, and the SDK's declared form of
    it is ledger row ``24.5-L-26``. This paragraph is a bounded correction
    (``D-07.1``): the token, the refusal type and this signature are
    unchanged.

    The sequence, and it is an order:

    1. **empty-operator guard** — unchanged from the local path, and fully
       meaningful across a boundary: a product declaring no operators was
       computed by nothing, whoever signed it (INV-CH7-46).
    2. **empty-operator result** — the guard's second half, by name
       (``24.5-L-24``): an operator RETURNED an empty set. Adjacent to the
       declared half, as locally. The consumer ran no engine, so the
       observation arrives only if the caller threads ``empty_results``;
       ``None`` (the default, every pre-phase call site) is *not observed*
       and passes.
    3. **attributability** — ``content_hash(candidate) == attested_address``.
    4. **TTL bounds** — the same INV-CH7-48 bound against the same pinned
       MAX_TTL a locally assembled product is held to. Expiry is a property of
       the product and the consumer's clock and needs nothing the consumer
       lacks.
    5. **declared obligations** — the same :data:`GATE_DECLARED_OBLIGATIONS`
       step :func:`run_gates` runs last, against the consuming class's own
       :class:`~ccf.products.contract.ServeObligations` (``24.5-L-14``,
       ``24.5-L-26``; ``D-IMPL-237``). A federated candidate carries ``debt``
       too, so the debt half applies where the consuming class declares a
       ceiling; the lineage half applies as declared. Last, for the reason it
       is last locally: every universal gate precedes a declared one.

    Args:
        candidate: The product as the peer declares it, parsed from the bytes
            whose signature verified.
        attested_address: The content address of those bytes — the witness the
            signature check established. Never derived from ``candidate``:
            deriving it here would reintroduce exactly the self-witnessing this
            function exists to remove.
        now: The evaluation instant, supplied by the caller.
        registry: Control Plane the MAX_TTL is resolved from.
        product_class: The registered class carrying the pinned MAX_TTL — and,
            since ``24.5-L-14``, the serve obligations step 4 reads.
        debt_tolerance: As on :func:`run_gates`: may only tighten the class's
            declared ceiling; ``None`` (the default, every pre-phase call
            site) leaves the class's ceiling standing.
        empty_results: As on :func:`run_gates` (``24.5-L-24``): the operator
            keys observed to have returned empty, or ``None`` — the default
            and every pre-phase call site — for *not observed*, which passes.

    Returns:
        A :class:`ServableProduct` when every gate passes, otherwise the
        refusal of the *first* gate that did not, in the five-step order
        above.

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

    returned_empty = _refuse_empty_results(candidate, empty_results=empty_results)
    if returned_empty is not None:
        return returned_empty

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

    obligation = _refuse_declared_obligations(
        candidate, product_class=product_class, debt_tolerance=debt_tolerance
    )
    if obligation is not None:
        return obligation

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


def _refuse_empty_results(
    candidate: ContextProductContract,
    *,
    empty_results: frozenset[str] | None,
) -> EmptyResultRefusal | None:
    """Gate 1's second half, shared by both sequences: an operator returned nothing.

    Ledger row ``24.5-L-24`` (``D-IMPL-238`` second sentence). The two halves
    of the empty-operator gate are two assertions that shared one name:
    :func:`_refuse_empty_operators` refuses a product that DECLARED no
    operators (the SDK's half, INV-CH7-46), and this function refuses a
    product one of whose operators RETURNED an empty set (the Standard's
    half). They are adjacent in both runners, declared half first, and each
    names itself.

    ``empty_results`` is the engine's observation
    (:attr:`~ccf.projection.engine.ExecutionResult.empty_results`), threaded
    by the governed resolver as a keyword. ``None`` means *not observed* —
    a caller built before the observation existed, or a federated candidate
    whose engine ran in another fabric — and PASSES: the compatibility
    posture :func:`refuse_attestation` documents, so every pre-phase call
    site is byte-identical in behavior. The empty set is the engine's
    positive assertion that no operator returned empty, and passes too. A
    non-empty set refuses, naming the first key in sorted order and carrying
    all of them.

    Reads operator keys from the execution and nothing from the payload
    (``D-IMPL-238`` limb 3): a payload that happens to be empty is the
    product's business; an operator that produced nothing is the fabric's.
    """
    if empty_results is None or not empty_results:
        return None
    ordered = sorted(empty_results)
    return EmptyResultRefusal(
        gate=GATE_EMPTY_OPERATOR_RESULT,
        detail=(
            f"product {candidate.schema_name!r}: operator {ordered[0]!r} "
            f"returned an empty set (all such operators: {ordered}); an "
            "empty assembled set fails closed (24.5-L-24)"
        ),
        operator_key=ordered[0],
        empty_operators=frozenset(empty_results),
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
