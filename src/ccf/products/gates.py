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
runners hold the candidate to the per-attribute lineage obligation its
product class *declared* in
:class:`~ccf.products.contract.ServeObligations` (ledger row ``24.5-L-26``).
It runs LAST because it is the only *declared* gate: every universal gate
precedes it, and a class that obliges nothing
(:data:`~ccf.products.contract.NO_SERVE_OBLIGATIONS`) never reaches a
comparison. It reads the presence and non-emptiness of a NAMED payload member
and nothing else — a structural gate, never a payload gate (``D-IMPL-238``
reading ``D-IMPL-102`` limb 3). ``_GATE_TOKEN``, :class:`_ServableProductMeta`
and :class:`GateBypassError` are untouched by it: the step returns a refusal
before the token is minted, exactly as the four before it do.

**The tolerance step is not a gate (Phase 24.6, ``24.6-L-05``,
``D-IMPL-251`` C1/C2).** This gate carried a debt half until ``24.6-04``: a
class-declared ``D_c`` ceiling folded with the request's tolerance by ``min``.
It is gone. A class's debt figure is a *default* tolerance, not an obligation
and not a policy boundary, so it can no longer withhold context from a caller
who asked for more; and the comparison that does withhold — an applicable
declared tolerance against an observed ``D_c`` — belongs *after* admission,
where the product it withholds already exists. :class:`ToleranceExceededRefusal`
and :func:`refuse_over_tolerance` are that comparison (whitepaper §7.7.4–§7.7.8,
where Context Debt gates Forced LLM and Fail-Closed behavior). No token of it
joins either runner: ``D-IMPL-237``'s one gate mechanism and ``D-IMPL-238``'s
membership-by-name are untouched.

**The empty-operator gate has ONE half again, and that is a ruling (Phase
24.6, ledger row ``24.6-L-06``; ``D-IMPL-242`` amendment 1, ``D-IMPL-253``
Q11/Q12).** Two assertions once shared the name ``empty-operator-guard``: the
SDK's — a product that DECLARED no operators (INV-CH7-46) — and the
Standard's — an operator that RETURNED an empty set. ``24.5-L-24`` split them
into two named gates. ``24.6-05`` retires the second one entirely.

The declared half STAYS, unchanged (:data:`GATE_EMPTY_OPERATOR`,
:func:`_refuse_empty_operators`): a product computed by nothing is not
servable, and no evidence can make it so.

The returned half is SUPERSEDED. Dave, ruling Q12: *"An operator successfully
evaluating an empty graph did compute something. Calling it uncomputed
conflates absence of input with absence of execution. Serve computed-empty
with the evidence-derived Debt; then an applicable tolerance may cause the
shell response."* So the returned half's token, its refusal type and the
keyword by which both runners read the engine's record
(:attr:`~ccf.projection.engine.ExecutionResult.empty_results`) are gone —
spelled here as what they were rather than by name, so a reader grepping this
module for the retired identifiers finds none. The emptiness now travels as a
FINDING on the served product
(:class:`~ccf.products.contract.ComputedEmptyFinding`, written by the
governed resolver), and what a consumer does about it is governed by Context
Debt — which is derived from evidence and never from cardinality
(``D-IMPL-255`` (2): *"Cardinality never determines Context Debt. Evidence
determines Context Debt."*). An admitted computed-empty product may still be
withheld by :func:`refuse_over_tolerance`, which is the tolerance decision
above and not a gate.

This module holds no TTL values and no thresholds (CLAUDE.md §11, CINV-01):
a tolerance's number is the deployment's, the caller's or a policy's, never
this module's. Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Sized
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Final, Literal, Never, cast

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.invalidation import resolve_register
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.graph.protocols import SourceAttestation
from ccf.halflife.assessment import DebtAssessment
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    RegisteredProductClass,
)
from ccf.products.provenance import (
    Authority,
    EffectiveParameter,
    ProvenanceSource,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "DEBT_TOLERANCE_PARAMETER",
    "GATE_DECLARED_OBLIGATIONS",
    "GATE_EMPTY_OPERATOR",
    "GATE_LINEAGE_ATTRIBUTABILITY",
    "GATE_LINEAGE_EQUALITY",
    "GATE_SOURCE_ATTESTATION",
    "GATE_TTL_ANCHOR",
    "GATE_TTL_BOUNDS",
    "PYDANTIC_MODEL_FORMS",
    "AttestationRefusal",
    "DeclaredObligationRefusal",
    "EmptyOperatorRefusal",
    "refuse_dependency_invalidation",
    "GateBypassError",
    "GateRefusal",
    "LineageAttributionRefusal",
    "LineageMismatchRefusal",
    "ProductInvariantRefusal",
    "ServableProduct",
    "verify_gate_provenance",
    "ServableProductNotAModel",
    "TTLAnchorRefusal",
    "TTLRefusal",
    "ToleranceExceededRefusal",
    "refuse_attestation",
    "refuse_over_tolerance",
    "run_federated_gates",
    "run_gates",
]

# `empty-operator-guard` is the SDK's half of what was briefly a pair
# (24.5-L-24): a product DECLARING no operators (INV-CH7-46). The Standard's
# half — an operator RETURNING an empty set — was `empty-operator-result` for
# one phase and is retired at 24.6-05 under `D-IMPL-242` amendment 1: an
# operator that ran and found nothing COMPUTED, so its emptiness is a finding
# on the served product (`ccf.products.contract.ComputedEmptyFinding`) rather
# than a token in this roster. One gate, one token, one meaning.
GATE_EMPTY_OPERATOR = "empty-operator-guard"
GATE_LINEAGE_EQUALITY = "lineage-strict-equality"
GATE_LINEAGE_ATTRIBUTABILITY = "lineage-attributability"
GATE_TTL_BOUNDS = "ttl-bounds"

#: `D-IMPL-341` R-3: gate 3's SECOND reason. A class declaring an evidence
#: anchor whose served observation set supplies no usable instant is refused
#: here, by this name — never as ``ttl-bounds`` (which says an anchor exists
#: and its window has passed) and never by falling back to the decision
#: instant.
GATE_TTL_ANCHOR = "ttl-anchor-unresolvable"
GATE_SOURCE_ATTESTATION = "source-attestation"
#: ``D-IMPL-334``. Named for the question it asks — may this be served —
#: rather than for the write that moved the boundary. NOT a cascade and
#: NOT an event: a graph supersession records an invalidation boundary, and
#: a product whose snapshot predates it on an entity it touched is no longer
#: eligible. Nothing is notified and nothing is evicted.
GATE_DEPENDENCY_INVALIDATION = "dependency-invalidation"
# The ONE structural mechanism D-IMPL-237 licenses beyond the five tokens
# above, which D-IMPL-238 records by name as the membership it joins
# (24.5-L-14, 24.5-L-26). Not a payload gate (limb 3), not a second mechanism.
GATE_DECLARED_OBLIGATIONS = "declared-obligations"

#: The Standard's universal request parameter (``references/
#: Context_Product_Specification_Standard_v0-3.md`` §2.4) by which a caller
#: states the Context Debt it is willing to be served — a parameter NAME the
#: SDK owns and never a number.
#:
#: **Three authorities answer to this one name** (``D-IMPL-251`` C1/C2,
#: ``D-IMPL-240`` amendment 2, ``24.6-L-04``/``24.6-L-05``):
#:
#: * ``caller`` — the value on ``request.parameters``, enforced **as
#:   requested**, looser or tighter. The consumer owns fitness.
#: * ``default`` — the product class's
#:   :attr:`~ccf.products.contract.ServeObligations.default_debt_tolerance`,
#:   which fills an OMISSION and nothing else. A class preference does not
#:   withhold context from a caller who asked for more.
#: * ``policy`` — a ``maximum`` on this name in a Control Plane
#:   :class:`~ccf.controlplane.artifacts.PolicyConstraint`, resolved through
#:   :mod:`ccf.products.constraints` and enforced as governance.
#:
#: The fold happens exactly once, in the Authority layer, and what it produces
#: is an :class:`~ccf.products.provenance.EffectiveParameter` carrying the
#: authority that established the value — never a bare number, because a bare
#: number cannot say who set it (``D-IMPL-253`` Q1). The comparison against an
#: observed ``D_c`` is :func:`refuse_over_tolerance`, over a product the gates
#: already admitted.
#:
#: The request boundary is unchanged: the parameter must be declared by the
#: class's request contract or
#: :func:`~ccf.products.request.refuse_request` refuses it as undeclared, and
#: a declared, well-typed number outside ``[0, 1]`` is refused by name
#: (``not-a-proportion``; ``24.5-REVIEW.md`` WR-02, Dave, 2026-09-02) — so
#: what reaches a resolution is always a proportion.
#:
#: CINV-01, reasoned rather than assumed: this is mechanism vocabulary the SDK
#: owns — on the footing of the four request axes (subject, instant,
#: perspective, tier) — and never a value. No number, no threshold and no
#: default tolerance lives here or anywhere in ``src/``; the class's number is
#: authored in its product-class artifact, the policy's in a constraint
#: artifact, and the request's is the caller's.
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


class TTLAnchorRefusal(GateRefusal):
    """Gate 3's second reason (`D-IMPL-341` R-3): no evidence instant to anchor on.

    The class declares ``ttl_anchor: from_entity_freshness`` and the served
    observation set — the same set the freshness factor scores — carries no
    ``valid_from`` instant on a row declaring ``decay_basis: valid-from``. Kept
    distinct from :class:`TTLRefusal` (an anchor exists and its window has
    passed) and from the registration-time refusal
    (:class:`~ccf.products.expiry.TTLAnchorUndeclared`: no such row is
    declared at all), because the three call for three different remedies.

    Attributes:
        ttl_anchor: The declared anchor, as recorded.
        now: The decision instant the set was evaluated at.
        valid_from_rows: The observation types whose rows could have
            contributed — what the deployment declared.
        observation_types: The observation types the served set actually
            held — what the evidence was.
    """

    ttl_anchor: str
    now: datetime
    valid_from_rows: tuple[str, ...]
    observation_types: tuple[str, ...]


class DependencyInvalidationRefusal(GateRefusal):
    """``D-IMPL-334``: an entity this product touched moved after its snapshot.

    The product is not wrong about the past — it is **no longer eligible to be
    served as an answer about now**, which is a different claim and the reason
    this is a refusal rather than a debt signal. It names the entity, the
    boundary and the snapshot separately, because a refusal that said only
    "stale" would not let a reader tell which evidence moved.

    Args:
        entity_uri: The touched entity whose effective context changed.
        invalidated_from: The boundary — the superseding observation's instant.
        graph_snapshot_at: The snapshot this product was built at.
        cause: The claim identity that superseded.
    """

    entity_uri: str
    invalidated_from: datetime
    graph_snapshot_at: datetime
    cause: str


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
    """The declared-obligations gate: the product broke what its class obliged.

    SDK-defined per CLAUDE.md §11 — whitepaper §7.6 (the validation gates).
    The ONE structural mechanism ``D-IMPL-237`` licenses, under one token,
    :data:`GATE_DECLARED_OBLIGATIONS`. Derives from :class:`GateRefusal` for
    the reason :class:`AttestationRefusal` records: a product meets the
    fabric's one gate discipline, and the ``ServableProduct | GateRefusal``
    return union of :func:`run_gates` is unchanged by this refusal existing.
    The HTTP door maps this kind to ``409``; this module knows nothing of
    status codes.

    **One obligation as of ``24.6-04``** (``24.6-L-04``, ``D-IMPL-251`` C1=A).
    The debt half retired: a class's debt figure is a DEFAULT tolerance and not
    an obligation, so nothing about Context Debt refuses here any more. What
    withholds a product over an applicable tolerance is
    :func:`refuse_over_tolerance`, which is not a gate — see its docstring for
    why the distinction is load-bearing. The gate's membership under
    ``D-IMPL-237``/``D-IMPL-238`` is unchanged by that move: the same token,
    the same two runners, one fewer code path inside it.

    Both sides are carried, in the :class:`TTLRefusal` voice: a caller never
    re-derives either to learn what the gap was.

    Attributes:
        obligation: Which declared obligation refused. One member —
            ``lineage-inputs``, a named payload member the class obliges that
            is absent or empty. A closed ``Literal`` rather than a free string
            so that a second obligation is an SDK decision and never a
            deployment's vocabulary.
        declared: What the class declared, rendered: the obliged member's name.
        observed: What the candidate carried, rendered: ``absent`` or
            ``empty``.
    """

    obligation: Literal["lineage-inputs"]
    declared: str
    observed: str


class ProductInvariantRefusal(GateRefusal):
    """A product class's OWN declared invariant refused, at runtime.

    SDK-defined per CLAUDE.md §11. The rulings of record are ``D-IMPL-282``
    (``R-11``, option 1a; Dave, 2026-09-08) and ``D-IMPL-224``, which made a
    product gate a declared, CI-checked property of a class. Dave's framing,
    which is the whole boundary: *"the runtime gate is not a new universal
    policy vocabulary. It is a declared product invariant with a governed
    identity, whose implementation is supplied by the deployment."*

    **What ``R-11`` supersedes, and what it leaves standing.**
    ``D-IMPL-225`` amendment 3 said of ``D-IMPL-224``'s declared gates:
    *"There is no ``ProductGate`` Protocol, no serve path for them, and the
    SDK's universal gates stay the only serve-time gates."* ``R-11``
    supersedes the **first two limbs and no more** — there is now a
    :class:`~ccf.products.resolver.ProductGateProtocol` and a path on which it
    runs. **The third limb stands.** This refusal is **not** produced by
    :func:`run_gates`, is not a member of its sequence, joins no token to the
    five-plus-one gate roster, and :data:`GATE_DECLARED_OBLIGATIONS` with its
    one-member ``Literal`` is untouched (``D-11``). Recorded here rather than
    only in a plan file, because a supersession that lives in a plan is one the
    next reader of this module will not find.

    **Where it DOES run**, so the call site is findable from here:
    :meth:`~ccf.products.resolver.GovernedResolver.__call__`, after
    :func:`run_gates` has ADMITTED a candidate and before
    :func:`refuse_over_tolerance` withholds one — the execution point
    ``D-IMPL-282`` names as *"after candidate construction and before
    fitness/fulfillment"* (``D-12``). It therefore never runs on a candidate
    the universal gates already refused: there is no product to hold an
    invariant against.

    It **derives** from :class:`GateRefusal` rather than paralleling it, on
    :class:`AttestationRefusal`'s and :class:`DeclaredObligationRefusal`'s
    stated reasoning: a product meets the fabric's one refusal discipline, not
    a second one that happens to look similar. The
    ``ServableProduct | GateRefusal`` return union of :func:`run_gates` is
    unchanged by this type existing, and the resolver's existing
    refusal-recording path carries it to replay with no second path.

    Attributes:
        gate: The declared ``gate_id``, inherited. Stamped by the resolver from
            the class's
            :attr:`~ccf.controlplane.artifacts.ProductClassDeclaration.declared_product_gate`
            and **never** supplied by the deployment's callable — which is what
            makes ``D-14``'s *"which gate produced the refusal"* a fact an
            examiner can trust rather than a claim the failing code made about
            itself.
        gate_version: The lane that id was declared at, stamped from the same
            declaration. Carried beside the id, in :class:`TTLRefusal`'s
            diagnostic-pair voice, so a reader of a refusal record resolves the
            exact gate a determination ran under rather than the one in force
            now.
        detail: What the deployment's callable returned — the violation, in the
            deployment's own words. The SDK reads it as text and never parses
            it: an invariant's failure mode is the product's to describe.
    """

    gate_version: str


def _refuse_declared_obligations(
    candidate: ContextProductContract,
    *,
    product_class: RegisteredProductClass,
) -> DeclaredObligationRefusal | None:
    """The declared-obligations gate, shared by both sequences — one function, one obligation.

    Factored rather than duplicated for the reason gates 1 and 3 are: the two
    runners cannot drift into two readings of what a class obliged.

    **The lineage obligation** (``24.5-L-26``). For each member the class names
    in ``lineage_inputs_at``, in sorted order so the named member is
    deterministic: absent or ``None`` → ``observed="absent"``; a sized value
    of length zero → ``observed="empty"``. Nothing else about the payload is
    read — presence and non-emptiness of a NAMED top-level member only. That
    is what keeps this a structural gate under ``D-IMPL-238``'s reading of
    ``D-IMPL-102`` limb 3: a payload whose named member holds anything at all
    serves, and no shape, type or schema is consulted.

    **What is no longer here** (``24.6-04``, ``24.6-L-04``). The debt half — a
    class-declared ceiling folded with the request's tolerance by ``min`` — is
    deleted, with the ``debt_tolerance`` keyword both runners carried. A class
    figure is a default (``D-IMPL-251`` C1=A: *"a product class cannot
    independently withhold otherwise deliverable context because its own debt
    preference was exceeded"*), and the tolerance comparison belongs after
    admission rather than inside a gate.

    Returns:
        ``None`` when the declared obligation holds, otherwise the refusal
        naming the first member that did not.
    """
    obligations = product_class.serve_obligations
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


def verify_gate_provenance(product: object) -> "ServableProduct":
    """Establish that ``product`` came through the three validation gates.

    `D-IMPL-337`'s verifier for :class:`ServableProduct`. **The check is the
    provenance, not the type**, and the difference is exploitable rather than
    academic: `isinstance` admits a subclass that skipped the guarded
    ``__init__`` and admits ``object.__new__``, both of which were measured
    reaching a served product with no gate having run.

    Returns the value, narrowed, so a caller writes
    ``product = verify_gate_provenance(product)`` and cannot forget to use the
    result.

    **Internal callees do not repeat this.** `D-IMPL-337` governs the boundary
    where an externally substitutable value arrives; everything downstream of
    an established value inherits it.

    Raises:
        GateBypassError: the value did not come through :func:`run_gates`.
            Raised rather than refused: a value with no gate provenance is not
            a product whose governance failed, it is not a governed product at
            all, and reporting it as a refusal would make an absent gate look
            like a gate that said no.
    """
    if getattr(product, "_gate_provenance", None) is not _GATE_TOKEN:
        raise GateBypassError(
            "this value carries no evidence of having passed the three"
            " validation gates. ccf.products.gates.run_gates is the only path"
            " that establishes it, and neither a structurally compatible"
            " object nor a subclass of ServableProduct that skipped its"
            " guarded __init__ acquires it (D-IMPL-337; whitepaper §7.6,"
            " INV-CH7-52)"
        )
    return cast(ServableProduct, product)


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
        # `D-IMPL-337`. The PROVENANCE, distinct from the type. Set only here,
        # on the only path that runs the gates — so a value that has it came
        # through that path, and `isinstance` says nothing about whether it
        # did. Measured before this line existed: `class F(ServableProduct)`
        # skipping `super().__init__` passed `isinstance` and reached a served
        # product with the gates never run.
        self._gate_provenance = _GATE_TOKEN

    @property
    def product(self) -> ContextProductContract:
        """The validated contract, ready for delivery."""
        return self._product


class ToleranceExceededRefusal(CCFContract):
    """Fulfillment withheld: an applicable declared tolerance was exceeded.

    SDK-defined per CLAUDE.md §11; whitepaper §7.7.4–§7.7.8 (Context Debt as
    the quantified shortfall that gates Forced LLM and Fail-Closed behavior).
    Ledger row ``24.6-L-05``; ``D-IMPL-251`` C2=B, and ``D-IMPL-253`` Q10 in
    Dave's own words: *"``tolerance-exceeded`` is right. Preserve which
    authority established the tolerance. I would not make the shell itself
    imply that Debt is invalid; the product was constructible, but fulfillment
    was withheld because an applicable declared tolerance was exceeded."*

    **What the shell says, and what it deliberately does not.** It says the
    fabric built the product and then withheld it. It does not say the Context
    Debt was wrong, unacceptable in itself, or a defect: a measured ``D_c`` is
    a truthful statement about the evidence, and the only thing that made it
    dispositive here is a tolerance somebody declared. Which somebody is the
    ``authority`` field, and it is carried precisely because a bare number
    cannot say who set it (``D-IMPL-253`` Q1).

    **This is NOT a gate.** ``D-IMPL-237`` licenses exactly one structural
    serve-time gate mechanism and ``D-IMPL-238`` records its membership by
    name; neither is touched by this type existing. It derives from
    :class:`~ccf.contracts.base.CCFContract` rather than from
    :class:`GateRefusal`, carries no ``gate`` token, and is returned by
    :func:`refuse_over_tolerance` — a comparison over a product the gate
    sequence has already ADMITTED, run by the layer that composes assembly and
    delivery. The distinction is the ruling: a gate decides whether a product
    may exist; this decides whether an existing product is delivered. Since it
    declares neither ``gate`` nor ``reason``,
    :func:`~ccf.products.refusal.envelope_for` reports the kind token
    (``tolerance-exceeded``) as the envelope's reason — *the most specific true
    thing that can be said about why*.

    Attributes:
        authority: Who established the tolerance —
            :data:`~ccf.products.provenance.Authority`, in practice
            ``default`` (the product class's
            :attr:`~ccf.products.contract.ServeObligations.default_debt_tolerance`,
            applied because the caller stated none), ``caller`` (the value on
            the request, honored as asked) or ``policy`` (a Control Plane
            constraint bounding this parameter). Not narrowed to those three:
            the Authority layer owns the vocabulary and this shell reports what
            it resolved.
        source: Where that authority's statement came from — the product-class
            artifact pin, the request's own identity, or the constraint
            artifact's ``(key, version)``. An examiner resolves the tolerance
            from this rather than taking the number on trust.
        tolerance: The applicable tolerance, the value the observation was
            compared against.
        observed: The product's Context Debt, or ``None`` when the product
            carries no assessment at all. ``None`` is a positive statement —
            *no assessment was produced* — and not a zero: an unmeasured
            product is neither within an applicable tolerance nor over it, and
            reporting it as ``0`` would claim a measurement nobody made.
        breakdown: The full :class:`~ccf.halflife.assessment.DebtAssessment`
            behind ``observed`` — the factors, the signal and the scorers in
            force — so a consumer can see *why* the debt is what it is rather
            than re-deriving it, or ``None`` when there was no assessment.
            This is the *"debt information that can safely be disclosed"* of
            ``D-IMPL-251`` C2; what of it actually crosses a door is the
            disclosure layer's decision, not this type's.
        detail: The sentence an operator reads in a log. It states that
            fulfillment was withheld and never that the Debt was wrong.
    """

    authority: Authority
    source: ProvenanceSource
    tolerance: Decimal
    observed: Decimal | None
    breakdown: DebtAssessment | None
    detail: str


def refuse_over_tolerance(
    product: ServableProduct,
    *,
    tolerance: EffectiveParameter | None,
) -> ToleranceExceededRefusal | None:
    """Hold an ADMITTED product to the one applicable tolerance, or serve it.

    SDK-defined per CLAUDE.md §11; whitepaper §7.7.4–§7.7.8. Ledger row
    ``24.6-L-05``, realizing ``D-IMPL-251`` C1=A and C2=B through
    ``D-IMPL-253`` Q10.

    **The argument is a resolved parameter, never a number.** The three debt
    authorities — the class's default, the caller's declared tolerance, an
    applicable policy constraint — are folded exactly once, upstream, by
    :func:`~ccf.products.constraints.resolve_effective_request`, and what
    arrives here is the single
    :class:`~ccf.products.provenance.EffectiveParameter` that fold produced.
    This function performs no fold of its own: a second fold is precisely the
    scalar collapse ``D-IMPL-254`` removed, and it would also be the place a
    class preference could quietly re-acquire the power ``C1`` took from it.

    **Not a gate** — see :class:`ToleranceExceededRefusal`. The product has
    already passed :func:`run_gates`; it exists, it is servable, and what is
    decided here is fulfillment.

    Args:
        product: The gate-admitted product. Taking a
            :class:`ServableProduct` rather than a candidate contract is the
            sequencing made structural: this comparison cannot be reached by a
            caller who has not run the gates, because it has nothing to pass.
        tolerance: The resolved tolerance for
            :data:`DEBT_TOLERANCE_PARAMETER`, or ``None`` when no authority
            stated one. ``None`` serves at any Debt — not a permissive
            default but the absence of any declaration to enforce, which is
            what a class declaring no default, a caller stating nothing and a
            deployment registering no constraint jointly mean.

    Returns:
        ``None`` when the product is delivered — no applicable tolerance, or
        an observed ``D_c`` at or under it — otherwise the
        :class:`ToleranceExceededRefusal` naming the authority, the tolerance
        and what was observed.
    """
    # `D-IMPL-337`. A governed boundary: exported, and the tolerance below is
    # held against a product whose gate authority this function relies on.
    product = verify_gate_provenance(product)

    if tolerance is None:
        return None
    presented = tolerance.value
    if isinstance(presented, bool) or not isinstance(presented, (int, Decimal)):
        # The same reading of "is this a number" that the request boundary
        # applies (`ccf.products.request::_refuse_tolerance`): `bool` is an
        # `int` to Python and not to the contract, and a `float` never reaches
        # a resolution at all because `EffectiveParameter` refuses one at
        # construction. Anything else is a wiring failure rather than a
        # governed determination, so it raises (`D-IMPL-253` amendment 2 (3)).
        raise TypeError(
            f"the effective {tolerance.name!r} resolved to"
            f" {type(presented).__name__}, which is not a numeric proportion;"
            " a tolerance the fabric cannot compare against D_c is a"
            " configuration failure, not a governed determination"
        )
    limit = Decimal(presented)
    assessment = product.product.debt
    if assessment is None:
        return ToleranceExceededRefusal(
            authority=tolerance.authority,
            source=tolerance.source,
            tolerance=limit,
            observed=None,
            breakdown=None,
            detail=(
                f"the product was constructible; fulfillment was withheld"
                f" because an applicable declared tolerance"
                f" ({tolerance.authority}) of {limit} cannot be shown to be"
                " met — the product carries no Context Debt assessment, so"
                " the observation the tolerance speaks about was never made"
                " (whitepaper §7.7.4–§7.7.8; 24.6-L-05)"
            ),
        )
    if assessment.debt <= limit:
        return None
    return ToleranceExceededRefusal(
        authority=tolerance.authority,
        source=tolerance.source,
        tolerance=limit,
        observed=assessment.debt,
        breakdown=assessment,
        detail=(
            f"the product was constructible; fulfillment was withheld because"
            f" an applicable declared tolerance ({tolerance.authority}) of"
            f" {limit} was exceeded by the observed Context Debt"
            f" {assessment.debt} (whitepaper §7.7.4–§7.7.8; 24.6-L-05)"
        ),
    )


def run_gates(
    candidate: ContextProductContract,
    *,
    engine_resolved: frozenset[str],
    now: datetime,
    registry: ControlPlaneProtocol,
    product_class: RegisteredProductClass,
    source_attestation: SourceAttestation | None = None,
    touched_entities: tuple[str, ...] | None = None,
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
        touched_entities: The entity URIs this execution actually read —
            ``execution.touched_entities()``, the same value replay dimension 1
            records (``D-IMPL-334``). Keyword-only with a ``None`` default on
            the attestation gate's own precedent, so every prior call site is
            byte-for-byte unchanged in behavior: ``None`` means *the caller did
            not say*, and the dependency-invalidation gate passes. An empty
            tuple means *the caller said nothing was touched* — a different
            statement, which also passes. Supplied, the gate refuses a product
            any of whose entities moved after the snapshot it was built at.

    Returns:
        A :class:`ServableProduct` when every gate passes, otherwise the
        refusal of the *first* gate that did not. The order is: the
        empty-operator guard (``empty-operator-guard`` — the DECLARED half,
        and since ``24.6-05`` the only one: an operator that ran and returned
        nothing is served with a
        :class:`~ccf.products.contract.ComputedEmptyFinding` rather than
        refused, ``D-IMPL-242`` amendment 1), lineage strict equality, TTL
        bounds, source attestation, then — LAST, because every universal gate
        precedes a declared one — the :data:`GATE_DECLARED_OBLIGATIONS` step,
        which is silent for a class that obliges nothing (``D-IMPL-237``).

        A product this sequence admits may still be **withheld**: an
        applicable declared tolerance is held against its observed Context
        Debt by :func:`refuse_over_tolerance`, after admission, in the caller
        that composes this sequence (``24.6-L-05``). That is a fulfillment
        decision over a product that exists, not a gate, and no token of it
        joins the sequence above. A computed-empty product reaches that
        comparison like any other: its Debt is what the deployment's scorers
        derived from the evidence, never a figure this module chose.

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

    # `D-IMPL-334`. AFTER the TTL gate deliberately: expiry is a property
    # of the product alone and answerable without touching the Control
    # Plane's register, so the cheaper and more universal refusal stays
    # first. A product that is both expired and invalidated refuses as
    # expired, which is the older and better-understood answer.
    invalidated = refuse_dependency_invalidation(
        candidate, touched_entities=touched_entities, registry=registry
    )
    if invalidated is not None:
        return invalidated

    obligation = _refuse_declared_obligations(
        candidate, product_class=product_class
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
       computed by nothing, whoever signed it (INV-CH7-46). Its briefly-lived
       second half (``empty-operator-result``, ``24.5-L-24``) is retired here
       as locally (``D-IMPL-242`` amendment 1): a peer's product whose
       operators returned nothing was computed, and if the peer recorded the
       search it travels on the product as a
       :class:`~ccf.products.contract.ComputedEmptyFinding`.
    2. **attributability** — ``content_hash(candidate) == attested_address``.
    3. **TTL bounds** — the same INV-CH7-48 bound against the same pinned
       MAX_TTL a locally assembled product is held to. Expiry is a property of
       the product and the consumer's clock and needs nothing the consumer
       lacks.
    4. **declared obligations** — the same :data:`GATE_DECLARED_OBLIGATIONS`
       step :func:`run_gates` runs last, against the consuming class's own
       :class:`~ccf.products.contract.ServeObligations` (``24.5-L-26``;
       ``D-IMPL-237``). The lineage obligation applies as declared. Last, for
       the reason it is last locally: every universal gate precedes a declared
       one. As locally, an admitted federated product may still be withheld
       over an applicable tolerance by :func:`refuse_over_tolerance`, which is
       the consuming layer's call and not a step of this sequence
       (``24.6-L-05``).

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
            since ``24.5-L-14``, the serve obligations the last step reads.

    Returns:
        A :class:`ServableProduct` when every gate passes, otherwise the
        refusal of the *first* gate that did not, in the four-step order
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
        candidate, product_class=product_class
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


def refuse_dependency_invalidation(
    candidate: ContextProductContract,
    *,
    touched_entities: tuple[str, ...] | None,
    registry: ControlPlaneProtocol,
) -> DependencyInvalidationRefusal | None:
    """``D-IMPL-334`` — serve-time dependency invalidation.

    Refuses when any entity the product touched carries an invalidation
    boundary **later than the snapshot the product was built at**. Nothing is
    evicted and nothing is notified: the register is read, the product in hand
    is evaluated against it, and the answer is may-serve or may-not.

    ``touched_entities is None`` **passes**, and that is the compatibility
    posture :func:`refuse_attestation` established — a caller that does not
    supply the list gets the behavior it had before this gate existed, so every
    pre-``D-IMPL-334`` call site is unchanged. A caller that supplies an empty
    tuple has said the product touched nothing, which also passes, and means
    something different.

    The comparison is **strictly later**. A boundary at exactly the snapshot
    instant does not refuse: the product read the state as of that instant, and
    a change *at* it is already inside what the product saw.
    """
    if touched_entities is None:
        return None
    register = resolve_register(registry, tenant_id=candidate.tenant_id)
    if register is None:
        return None
    snapshot = candidate.lineage.graph_snapshot_at
    for entity_uri in touched_entities:
        entry = register.entry_for(entity_uri)
        if entry is None or entry.invalidated_from <= snapshot:
            continue
        return DependencyInvalidationRefusal(
            gate=GATE_DEPENDENCY_INVALIDATION,
            detail=(
                f"entity {entity_uri!r} was superseded at "
                f"{entry.invalidated_from.isoformat()}, after this product's "
                f"graph snapshot {snapshot.isoformat()}; the product is no "
                f"longer eligible to serve (D-IMPL-334)"
            ),
            entity_uri=entity_uri,
            invalidated_from=entry.invalidated_from,
            graph_snapshot_at=snapshot,
            cause=entry.source,
        )
    return None


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
