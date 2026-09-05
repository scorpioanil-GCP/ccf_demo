"""The one canonical refusal envelope — how a "no" crosses a delivery seam.

**SDK-defined, not whitepaper-derived.** The whitepaper specifies the Context
Product Contract (§6.3) and the three validation gates that refuse a candidate
(§7.6); it does not specify a transport shape for the refusals themselves,
because it does not specify a client. This module is the CCF SDK's extension,
ruled in ``docs/superpowers/specs/2026-08-15-ccf-client-design.md`` Amendment 1
§A and framed by CLAUDE.md §7.3 (the neutral seams — the typed contract, MCP,
A2A — are the stable layer). It inherits the whitepaper's contract discipline
by deriving from :class:`~ccf.contracts.base.CCFContract`: frozen,
``extra=forbid``, canonically serializable.

Why it exists
-------------
A served product has one shape every door already emits. A **refused** one had
none: the resolver seam is typed to return a servable product and admits no
refusal in its union, so every refusal type the fabric declares reached no
wire at all. There was nothing for a door to emit until this shape existed,
which is why the envelope is defined here — in ``src/``, beside the types it
carries — before any door is changed.

The two ruled constraints
-------------------------
**(a) Every refusal kind crosses without flattening.** The fabric declares
twenty-two of them: the ``GateRefusal`` hierarchy
(:mod:`ccf.products.gates`, including the declared-obligations refusal of
``24.5-L-14`` / ``24.5-L-26`` and the empty-operator gate's returned-empty
half of ``24.5-L-24``), the peering-admission refusals that derive from it
(:mod:`ccf.peering.admission`), the product-mount refusal that derives from it
(:mod:`ccf.graph.product_source`), the two request/payload conformity verdicts
(:mod:`ccf.products.request`, :mod:`ccf.products.payload`), the pre-assembly
anchor-ambiguity refusal beside them (:mod:`ccf.products.request`,
``24.5-L-16``), the two constraint-layer determinations
(:mod:`ccf.products.constraints`, ``24.6-L-07``), the assembly mixing refusal
(:mod:`ccf.products.composition`),
and the assembly-time refusal returned as a value
(:mod:`ccf.agents.errors`, ``24.5-L-11``). If the envelope lost *which
kind* a refusal was, a client's ``refusal.reason`` would become mush and the
auditable-refusal guarantee would die at the seam. So ``kind`` is a required
member sourced from :data:`REFUSAL_KINDS`, and every field a refusal type
declares of its own survives the crossing in :attr:`RefusalEnvelope.fields`.

**(b) It carries the pre-assembly request identity** — product id, parameters,
temporal boundary — as :class:`RequestIdentity`. The refusal types carry none
of this: they are values about *what was wrong*, not about *what was asked*.
The caller holding the request supplies it.

The peering and mount families are in scope deliberately
--------------------------------------------------------
:class:`~ccf.peering.admission.AdmissionRefusal` and
:class:`~ccf.graph.product_source.ProductMountRefusal` both derive from
:class:`~ccf.products.gates.GateRefusal` rather than paralleling it, and both
say why in their own docstrings: a caller inspecting ``gate`` and ``detail``
reads a peering refusal exactly as it reads a TTL refusal. An envelope that
carried the TTL refusal and dropped the admission refusal would break the very
property those modules were written to preserve. Whether either is reachable
from a particular door today is a fact about *reachability*; constraint (a) is
worded over the vocabulary.

What is deliberately **not** here
---------------------------------
* **Entitlement verdicts.** :class:`~ccf.products.entitlement.ProductEntitlementViolation`
  and its sibling are ``LookupError`` subclasses — *exceptions raised at a
  door*, not values returned by the fabric. Contract-level principal and
  entitlement handling at the client seam is deferred, so they are out of this
  envelope's vocabulary and are recorded in :data:`NON_VALUE_VIOLATIONS`.
* **Control Plane, harness and composition verdicts.** Four further
  contracts in the walked name families exist under ``src/`` — a registration
  verdict, a harness effect-capture verdict, a skilling-governance verdict, and
  an agent-composition default conflict. None crosses a product seam. They are
  recorded in :data:`NON_PRODUCT_REFUSALS`.

Both exclusions are **named asserted allowlists**, not omissions: the
exhaustiveness gate in ``tests/products/test_refusal_envelope.py`` closes each
by set equality against a structural walk of ``src/``. A new refusal type that
is neither translated nor allowlisted fails the build and demands a ruling
rather than shipping untranslated.

This module is algorithmic (CINV-03): pure functions over typed values, no
I/O, no clock, no LLM dependency ever.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Final

from ccf.agents.errors import AssemblyRefusal
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.graph.product_source import ProductMountRefusal
from ccf.peering.admission import (
    AdmissionRefusal,
    ContractRefusal,
    LineageContinuityRefusal,
    PayloadTooLargeRefusal,
    PolicyBindingRefusal,
    SignatureRefusal,
)
from ccf.products.composition import MixingRefusal
from ccf.products.constraints import ConstraintRefusal, PolicyResolutionConflict
from ccf.products.contract import ProductLineage
from ccf.products.gates import (
    AttestationRefusal,
    DeclaredObligationRefusal,
    EmptyOperatorRefusal,
    EmptyResultRefusal,
    GateRefusal,
    LineageAttributionRefusal,
    LineageMismatchRefusal,
    ToleranceExceededRefusal,
    TTLRefusal,
)
from ccf.products.payload import PayloadSchemaViolation
from ccf.products.request import AnchorAmbiguityRefusal, ProductRequestViolation

__ccf_mode__ = "algorithmic"

__all__ = [
    "NON_PRODUCT_REFUSALS",
    "NON_VALUE_VIOLATIONS",
    "REFUSAL_KINDS",
    "RefusalEnvelope",
    "RequestIdentity",
    "envelope_for",
]


class RequestIdentity(CCFContract):
    """What was asked, as it stood *before* assembly began.

    Constraint (b) of Amendment 1 §A. None of the refusal types carries any of
    this: a refusal is a value about what was wrong, and the question it was
    wrong about is held by the caller that asked it.

    Attributes:
        product_id: The product class the question addressed — the
            ``schema_name`` of the request.
        product_version: The class's own semver lane, or ``None`` when the
            question named none. Lanes are per class and never compared across
            classes.
        parameters: What the caller supplied. An empty mapping is a question
            that needed nothing beyond its axes — a statement, and not the same
            fact as *unknown*, which this type cannot express and does not need
            to.
        temporal_boundary: The instant the question was asked against. ``None``
            is the positive assertion *the caller deferred to the server's
            decision instant* rather than a missing value.
    """

    product_id: str
    product_version: str | None
    parameters: Mapping[str, Any]
    temporal_boundary: datetime | None


class RefusalEnvelope(CCFContract):
    """One shape carrying any shipped refusal, with nothing flattened out.

    Constraint (a) of Amendment 1 §A. The envelope is a *transport* shape: it
    restates no refusal's meaning and computes nothing. It promotes the four
    members every consumer needs to branch on, preserves everything else the
    refusal type declared in :attr:`fields`, and attaches the question and the
    lineage the refusal itself does not carry.

    **Promotion rules, applied by reflection over the refusal's declared
    fields** — never by a per-type table, so a field added to a refusal type
    next year appears here without an edit:

    ``reason``
        A :class:`~ccf.products.gates.GateRefusal` reports its ``gate``,
        because that is the token its whole family was designed to be read by.
        A refusal outside that family that declares a field named ``reason``
        reports it — the closed request and payload reason vocabularies. A
        refusal that declares neither reports its own :attr:`kind`.
    ``key``
        The value of a declared field named ``key``, or ``None``. A TTL refusal
        names no parameter, and saying so is not a loss.
    ``detail``
        The prose the refusal already carries, unchanged.
    ``fields``
        Every remaining declared field, including inherited ones — the whole
        MRO, so a three-level refusal keeps its leaf, middle and base fields
        alike. A member promoted above is not repeated here; a member that
        merely shares a *name* with a promotion that did not take it — a
        gate-family refusal's own ``reason`` field, say — is kept, because
        dropping it would be exactly the flattening this type exists to
        prevent.

    Attributes:
        kind: Which refusal type this was, from :data:`REFUSAL_KINDS`. The
            whole substance of constraint (a): a consumer that cannot name the
            kind cannot audit the refusal.
        reason: The refusal's own reason or gate token, per the rules above.
        key: What the refusal names, when it names one.
        detail: The refusal's human-readable statement, for an operator
            reading a log. The typed members are the machine-readable version;
            nothing should parse this string.
        fields: The refusal type's own declared fields, each rendered in the
            SDK's one canonical form (:func:`~ccf.contracts.canonical.canonical_bytes`),
            so a set arrives sorted, an instant arrives as RFC3339 UTC, and a
            string arrives quoted — which is what keeps a presented ``"3"``
            distinguishable from a presented ``3`` after the crossing.
        request: The question, as it stood before assembly.
        pre_assembly_lineage: The partial lineage that existed at the point of
            refusal, or ``None`` when the refusal preceded assembly entirely.
            The distinction is load-bearing and is carried rather than
            flattened: a request-conformity verdict is reached before the graph
            is touched and *has* no lineage, while a payload verdict or any
            gate refusal has a candidate contract behind it and therefore a
            real, non-empty answer. ``None`` here is the positive assertion
            *there was none*, not *it was dropped*.
    """

    kind: str
    reason: str
    key: str | None
    detail: str
    fields: Mapping[str, str]
    request: RequestIdentity
    pre_assembly_lineage: ProductLineage | None


#: Every refusal type the fabric ships, mapped to the token that names it on
#: the wire. Mechanism, not values: it maps SDK types to SDK tokens and holds
#: no deployment's vocabulary (CINV-01).
#:
#: **Closed, and closed by equality.** The exhaustiveness gate in
#: ``tests/products/test_refusal_envelope.py`` walks ``src/`` structurally and
#: asserts this mapping's key set equals what the tree declares, minus the two
#: allowlists below. A type added to the tree and not added here fails the
#: build; a token declared here whose type no longer ships fails it too.
REFUSAL_KINDS: Final[Mapping[type[CCFContract], str]] = {
    # The three-gate family (whitepaper §7.6), the additive attestation
    # gate beside it, and the ONE structural declared-obligations gate
    # D-IMPL-237 licenses — the kind the HTTP door maps to 409. As of
    # 24.6-04 that gate carries ONE obligation (`lineage-inputs`, 24.5-L-26):
    # the debt half and the 409 DEBT route it served are retired, because a
    # class's debt figure is a default tolerance rather than an obligation
    # (`D-IMPL-251` C1=A). The kind and its 409 mapping stand for the lineage
    # obligation. The empty-operator gate's two halves are two kinds
    # (24.5-L-24): a product that DECLARED no operators, and an operator that
    # RETURNED an empty set. `empty-result-refusal` was chosen over
    # `empty-operator-result-refusal` because neither of the pair is a
    # substring of the other under the closure gate's rule, and the shorter
    # name reads as what it is.
    GateRefusal: "gate-refusal",
    EmptyOperatorRefusal: "empty-operator-refusal",
    EmptyResultRefusal: "empty-result-refusal",
    LineageMismatchRefusal: "lineage-mismatch-refusal",
    LineageAttributionRefusal: "lineage-attribution-refusal",
    TTLRefusal: "ttl-refusal",
    AttestationRefusal: "attestation-refusal",
    DeclaredObligationRefusal: "declared-obligation-refusal",
    # Beside it and deliberately NOT of it (24.6-L-05, `D-IMPL-251` C2=B):
    # `tolerance-exceeded` is not a gate token and `ToleranceExceededRefusal`
    # is not a `GateRefusal`. The gates admitted the product; an applicable
    # declared tolerance — the class's default, the caller's own value or a
    # policy constraint — then withheld its fulfillment, and the shell carries
    # which authority set it. The token is post-assembly (a candidate existed,
    # so it is NOT in `_PRE_ASSEMBLY_REFUSALS`), and no shipped token is a
    # substring of it or it of them. Which door class it maps to is plan 09's
    # question; the DEBT half of the 409 route retired with the gate half.
    ToleranceExceededRefusal: "tolerance-exceeded",
    # The peering-admission family, which derives from the gate family rather
    # than paralleling it (CLAUDE.md §7.2).
    AdmissionRefusal: "admission-refusal",
    PayloadTooLargeRefusal: "payload-too-large-refusal",
    SignatureRefusal: "signature-refusal",
    ContractRefusal: "contract-refusal",
    PolicyBindingRefusal: "policy-binding-refusal",
    LineageContinuityRefusal: "lineage-continuity-refusal",
    # The mount refusal, on the same derivation argument.
    ProductMountRefusal: "product-mount-refusal",
    # The two conformity verdicts — named for what they are rather than for
    # the gate family they deliberately do not join — and, beside them, the
    # pre-assembly refusal for an anchor that resolves to more than one
    # entity (24.5-L-16). The SDK names the kind; who is ambiguous, and what a
    # product does about it, stays the product's.
    ProductRequestViolation: "product-request-violation",
    PayloadSchemaViolation: "payload-schema-violation",
    AnchorAmbiguityRefusal: "anchor-ambiguity-refusal",
    # The two constraint-layer determinations (24.6-L-07, D-IMPL-253 Q4/Q7),
    # reached while the effective request is being resolved and therefore
    # before the graph is touched. `constraint-refusal` is a value the fabric
    # may not act on — the caller's or the class's, held to a policy or a
    # technical bound; `policy-resolution-conflict` is the deployment's own
    # policy set disagreeing with itself, which is the shell that exists so
    # priority never has to erase an applicable hard constraint. Neither token
    # is a substring of `contract-refusal` or `policy-binding-refusal`, the two
    # shipped tokens they read closest to, and the closure gate checks that
    # rather than leaving it to the eye.
    ConstraintRefusal: "constraint-refusal",
    PolicyResolutionConflict: "policy-resolution-conflict",
    # The assembly-time mixing rule, which is not a fourth gate.
    MixingRefusal: "mixing-refusal",
    # The assembly-time refusal returned as a value — the exception of the
    # same name stays a raise (24.5-L-11). A second channel beside
    # `AssemblyRefused`, never a translation of it: no door catches the raise.
    AssemblyRefusal: "assembly-refusal",
}

#: ``…Refusal``-named contracts under ``src/`` that are **not** product
#: refusals. Each is a verdict on a path that never reaches a product seam, so
#: none belongs in the envelope's vocabulary:
#:
#: * ``RegistrationRefusal`` — a Control Plane registration verdict.
#: * ``EffectRefusal`` — a harness effect-capture verdict (CLAUDE.md §7.3,
#:   seam 3).
#: * ``GrantRefusal`` — a skilling-governance verdict (CLAUDE.md §6.2).
#: * ``DefaultConflict`` — an agent-composition verdict: two archetypes
#:   contributing the same default. It joined this allowlist in ``24.6-L-07``,
#:   when the structural walk widened to the ``…Conflict`` name family so that
#:   :class:`~ccf.products.constraints.PolicyResolutionConflict` could not
#:   enter the vocabulary by exemption. It has been in ``src/`` since the agent
#:   framework shipped and reaches no product seam.
#:
#: An allowlist rather than an omission: the gate asserts this set equals
#: exactly what the structural walk found and could not place, so a fifth
#: such class demands a ruling instead of passing unseen.
NON_PRODUCT_REFUSALS: Final[frozenset[str]] = frozenset(
    {"RegistrationRefusal", "EffectRefusal", "GrantRefusal", "DefaultConflict"}
)

#: ``…Violation``- and ``…Conflict``-named classes under ``src/`` that are
#: **exceptions rather than values**, and therefore outside an envelope that
#: carries returned refusals:
#:
#: * ``TrustPolicyViolation`` — raised on a peering-trust lookup.
#: * ``SnapshotScopeViolation`` — raised on a replay-snapshot scope miss.
#: * ``ProductEntitlementViolation`` — raised at a door; contract-level
#:   principal and entitlement handling at the client seam is deferred.
#: * ``SingleWriterViolation`` — the single-writer invariant firing
#:   (CLAUDE.md §10).
#: * ``WebhookEndpointConflict`` — raised when two HITL webhook registrations
#:   claim one endpoint.
#: * ``FragmentFamilyConflict`` — raised when two projection fragments claim
#:   one family.
#: * ``ConstraintEffectivityConflict`` — raised when the Control Plane holds
#:   two authoritative statements in force at one instant and they disagree.
#:   **Deliberately an exception and not a governed shell** (``D-IMPL-253``
#:   Q15, Dave: *"retain exceptions for actual configuration/invariant
#:   contradictions"*): a governed "no" is a determination the fabric reached,
#:   while two contradicting authoritative inputs are a state in which it
#:   cannot determine what is true.
#:
#: The last two joined in ``24.6-L-07`` for the reason ``DefaultConflict``
#: joined the allowlist above: the structural walk widened to the ``…Conflict``
#: name family so that
#: :class:`~ccf.products.constraints.PolicyResolutionConflict` could not enter
#: the vocabulary by exemption, and widening a walk means placing everything it
#: then finds. Both are pre-existing ``ValueError`` subclasses and neither
#: changed.
#:
#: This is the second allowlist, and it exists so the exception half of the
#: name vocabulary closes by equality too. Two ``…Violation``-named classes
#: *are* in :data:`REFUSAL_KINDS`; they get there because their base resolves
#: to :class:`~ccf.contracts.base.CCFContract`, never because a constant names
#: them. Without this set the half a ``…Refusal``-only walk cannot reach would
#: stay enumerated by hand, and a new contract-based ``…Violation`` would ship
#: untranslated with the gate green.
NON_VALUE_VIOLATIONS: Final[frozenset[str]] = frozenset(
    {
        "TrustPolicyViolation",
        "SnapshotScopeViolation",
        "ProductEntitlementViolation",
        "SingleWriterViolation",
        "WebhookEndpointConflict",
        "FragmentFamilyConflict",
        "ConstraintEffectivityConflict",
    }
)


#: Refusal types reached **before** the graph is touched, and which therefore
#: cannot have a pre-assembly lineage. Offering one alongside such a refusal is
#: a category error rather than extra information, so :func:`envelope_for`
#: refuses it — which is what makes D-09's assembly-boundary split structural
#: instead of conventional. A payload verdict and every gate refusal have a
#: candidate contract behind them and are deliberately absent from this set.
#:
#: Private: it is a statement about *when* the fabric reaches a refusal, not a
#: second vocabulary, and it is not part of this module's exported surface.
#:
#: :class:`~ccf.products.request.AnchorAmbiguityRefusal` joined in ``24.5-L-16``:
#: an anchor resolves before the graph is touched, so offering it a lineage is
#: the same false claim.
#:
#: :class:`~ccf.products.constraints.ConstraintRefusal` and
#: :class:`~ccf.products.constraints.PolicyResolutionConflict` joined in
#: ``24.6-L-07`` on the same argument: both are reached while the *effective
#: request* is being resolved, which is strictly before an operator plan is
#: built, so a lineage offered with either would claim evidence that could not
#: exist yet.
_PRE_ASSEMBLY_REFUSALS: Final[frozenset[type[CCFContract]]] = frozenset(
    {
        ProductRequestViolation,
        AnchorAmbiguityRefusal,
        ConstraintRefusal,
        PolicyResolutionConflict,
    }
)


def _render(value: object) -> str:
    """One field value in the SDK's one canonical form.

    Not ``str()``: a ``frozenset`` has no stable ``repr`` ordering and a
    ``datetime`` has no single textual form, and both reach an audit record
    through this envelope. :func:`~ccf.contracts.canonical.canonical_bytes` is
    the SDK's single answer to both, so this module defines no second one.
    """
    return canonical_bytes(value).decode("utf-8")


def envelope_for(
    refusal: object,
    *,
    request: RequestIdentity,
    pre_assembly_lineage: ProductLineage | None = None,
) -> RefusalEnvelope:
    """Translate any shipped refusal into the one envelope, losing nothing.

    Total over :data:`REFUSAL_KINDS` and defined nowhere else: a type this
    mapping does not name raises rather than receiving a best-effort envelope.

    **Dispatch is on the exact type, never ``isinstance``.** An ``isinstance``
    chain would translate an unknown subclass as its nearest known ancestor and
    report that ancestor's kind — a flattening that produces a perfectly
    well-formed envelope carrying the wrong answer, which is the failure mode
    hardest to notice and exactly the one constraint (a) forbids.

    **The promoted members are found by reflection over the refusal's declared
    fields**, so a field added to a refusal type appears in the envelope with no
    edit here, and the exhaustiveness gate has live structure to check rather
    than a transcription to agree with. See :class:`RefusalEnvelope` for the
    three promotion rules.

    Args:
        refusal: A value of any type named in :data:`REFUSAL_KINDS`.
        request: The question this refusal answers, which the refusal itself
            does not carry — the caller holding the request supplies it.
        pre_assembly_lineage: The partial lineage that existed at the point of
            refusal, when one did. Must be ``None`` for a refusal the fabric
            reaches before touching the graph.

    Returns:
        The envelope, carrying the kind, the promoted members, every remaining
        declared field canonically rendered, the request, and the lineage or
        its explicit absence.

    Raises:
        TypeError: ``refusal`` is not an instance of a type this module
            translates. The message names the type, because the two ways to
            resolve it are both deliberate acts — translate it in
            ``src/ccf/products/refusal.py``, or record it in one of the two
            allowlists with its reason.
        ValueError: a lineage was offered alongside a refusal reached before
            assembly began.
    """
    # One guard for both ways of not being a refusal — not a contract at all,
    # or a contract this module does not translate. They are the same defect
    # from the caller's side and get the same message.
    if not isinstance(refusal, CCFContract) or type(refusal) not in REFUSAL_KINDS:
        raise TypeError(
            f"{type(refusal).__name__} is not a refusal type this envelope"
            " translates; add it to REFUSAL_KINDS in"
            " `src/ccf/products/refusal.py`, or to NON_PRODUCT_REFUSALS or"
            " NON_VALUE_VIOLATIONS with its reason"
        )
    kind = REFUSAL_KINDS[type(refusal)]

    if pre_assembly_lineage is not None and type(refusal) in _PRE_ASSEMBLY_REFUSALS:
        raise ValueError(
            f"{type(refusal).__name__} is reached before the graph is touched,"
            " so it has no pre-assembly lineage; pass None"
        )

    declared = tuple(type(refusal).model_fields)
    consumed: set[str] = set()

    if isinstance(refusal, GateRefusal):
        # The gate token is what the whole family was designed to be read by,
        # so it wins even on the one type that also declares a `reason`.
        reason = refusal.gate
        consumed.add("gate")
    elif "reason" in declared:
        reason = str(getattr(refusal, "reason"))
        consumed.add("reason")
    else:
        # A refusal declaring neither is still a refusal; its kind is the most
        # specific true thing that can be said about why.
        reason = kind

    key: str | None = None
    if "key" in declared:
        key = str(getattr(refusal, "key"))
        consumed.add("key")

    detail = ""
    if "detail" in declared:
        detail = str(getattr(refusal, "detail"))
        consumed.add("detail")

    fields = {
        name: _render(getattr(refusal, name))
        for name in declared
        if name not in consumed
    }

    return RefusalEnvelope(
        kind=kind,
        reason=reason,
        key=key,
        detail=detail,
        fields=fields,
        request=request,
        pre_assembly_lineage=pre_assembly_lineage,
    )
