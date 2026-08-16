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
sixteen of them across three families: the ``GateRefusal`` hierarchy
(:mod:`ccf.products.gates`), the peering-admission refusals that derive from it
(:mod:`ccf.peering.admission`), the product-mount refusal that derives from it
(:mod:`ccf.graph.product_source`), the two request/payload conformity verdicts
(:mod:`ccf.products.request`, :mod:`ccf.products.payload`), and the assembly
mixing refusal (:mod:`ccf.products.composition`). If the envelope lost *which
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
* **Control Plane and harness verdicts.** Three further ``…Refusal``-named
  contracts exist under ``src/`` — a registration verdict, a harness
  effect-capture verdict, and a skilling-governance verdict. None crosses a
  product seam. They are recorded in :data:`NON_PRODUCT_REFUSALS`.

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
from ccf.products.contract import ProductLineage
from ccf.products.gates import (
    AttestationRefusal,
    EmptyOperatorRefusal,
    GateRefusal,
    LineageAttributionRefusal,
    LineageMismatchRefusal,
    TTLRefusal,
)

# These two imports are ordered ``request`` before ``payload`` deliberately,
# and the order is load-bearing. A pre-existing cycle in the tree —
# ``ccf.products.payload`` → ``ccf.skills.catalog`` → ``ccf.agents`` →
# ``ccf.replay.record`` → ``ccf.products.request`` → ``ccf.products.payload``
# — makes ``import ccf.products.payload`` raise ``ImportError`` when it is the
# first entry into that cycle, on the tree as it stands and with or without
# this module. Entering through ``ccf.products.request`` completes the cycle's
# far side first and both modules then load. The defect is not this module's to
# fix (nothing here may modify an existing module), so it is pinned instead:
# ``tests/products/test_refusal_envelope.py`` imports this module in a cold
# subprocess, and a reordering of these two lines fails that test rather than
# breaking an adopter's first import.
from ccf.products.request import ProductRequestViolation
from ccf.products.payload import PayloadSchemaViolation

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
    # The three-gate family (whitepaper §7.6), and the additive attestation
    # gate beside it.
    GateRefusal: "gate-refusal",
    EmptyOperatorRefusal: "empty-operator-refusal",
    LineageMismatchRefusal: "lineage-mismatch-refusal",
    LineageAttributionRefusal: "lineage-attribution-refusal",
    TTLRefusal: "ttl-refusal",
    AttestationRefusal: "attestation-refusal",
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
    # the gate family they deliberately do not join.
    ProductRequestViolation: "product-request-violation",
    PayloadSchemaViolation: "payload-schema-violation",
    # The assembly-time mixing rule, which is not a fourth gate.
    MixingRefusal: "mixing-refusal",
}

#: ``…Refusal``-named contracts under ``src/`` that are **not** product
#: refusals. Each is a verdict on a path that never reaches a product seam, so
#: none belongs in the envelope's vocabulary:
#:
#: * ``RegistrationRefusal`` — a Control Plane registration verdict.
#: * ``EffectRefusal`` — a harness effect-capture verdict (CLAUDE.md §7.3,
#:   seam 3).
#: * ``GrantRefusal`` — a skilling-governance verdict (CLAUDE.md §6.2).
#:
#: An allowlist rather than an omission: the gate asserts this set equals
#: exactly what the structural walk found and could not place, so a fourth
#: such class demands a ruling instead of passing unseen.
NON_PRODUCT_REFUSALS: Final[frozenset[str]] = frozenset(
    {"RegistrationRefusal", "EffectRefusal", "GrantRefusal"}
)

#: ``…Violation``-named classes under ``src/`` that are **exceptions rather
#: than values**, and therefore outside an envelope that carries returned
#: refusals:
#:
#: * ``TrustPolicyViolation`` — raised on a peering-trust lookup.
#: * ``SnapshotScopeViolation`` — raised on a replay-snapshot scope miss.
#: * ``ProductEntitlementViolation`` — raised at a door; contract-level
#:   principal and entitlement handling at the client seam is deferred.
#: * ``SingleWriterViolation`` — the single-writer invariant firing
#:   (CLAUDE.md §10).
#:
#: This is the second allowlist, and it exists so the ``…Violation`` half of
#: the name vocabulary closes by equality too. Two ``…Violation``-named classes
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
_PRE_ASSEMBLY_REFUSALS: Final[frozenset[type[CCFContract]]] = frozenset(
    {ProductRequestViolation}
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
