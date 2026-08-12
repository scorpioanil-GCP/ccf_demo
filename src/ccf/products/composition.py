"""How an aggregate product's lineage, expiry and mixing legality compose.

Whitepaper §6.4 Lifecycle Step 4 (``docs/CCF_Whitepaper_1-2.md:1483``):
*"Temporal Validation refuses to assemble a product that silently mixes the
two"* — the ninety-day filing and the fifteen-minute blotter entry. The ruling
of record is ``docs/DECISIONS.md`` **D-IMPL-31** (Dave, 2026-07-25), which
resolved TTL granularity as two granularities with a declared derivation rule:

    ``expires_at = min(class-configured MAX_TTL ceiling per D-IMPL-39,
    derivation over constituent signal validities)``

and, in the same entry, ruled that *"product classes may declare
constituent-validity floors whose breach refuses assembly rather than emitting
a product fresher-labeled than its stalest load-bearing constituent (the
mixing-refusal rule, formally footed)."* The floors were declared in
:class:`~ccf.products.contract.ConstituentValidityFloors`; **this module is the
refusal that reads them**, and it sits at assembly rather than at registration
because the mix does not exist until assembly.

Three limbs, and one that is deliberately absent
------------------------------------------------

* :func:`compose_lineage` — the N-way set-union, so every constituent's source
  signal stays resolvable from the composite.
* :func:`compose_expiry` — the TTL floor, so a composite is never labelled
  fresher than the constituent that ages out first.
* :func:`refuse_mixing` — D-IMPL-31's mixing-refusal rule.

**There is no debt composition here, by ruling and not by oversight.**
``docs/DECISIONS.md`` **D-IMPL-104** (Dave, 2026-08-11) ruled the *meaning* of
aggregate debt — it is the **per-factor maximum across constituents**,
worst factor wins, recorded as consistent with D-IMPL-31's own discipline of
taking the most constraining constituent rather than as a new axiom — and
**deferred the implementation** until an aggregate-product surface exists to
carry it. Dave's direction in that entry is explicit: *"Implementation can wait
until the surface appears; the meaning cannot."* When the surface arrives the
combinator is one pure function beside
:func:`~ccf.halflife.debt.context_debt`, it adds no new weights, and it
therefore does not disturb that module's multiplicative-conjunctive commitment
(``src/ccf/halflife/debt.py``: *"There is no weighted-additive alternative in
this module to fall back to."*). A reader looking for ``compose_debt`` should
find this paragraph, not a gap.

What this module is **not**: an aggregate-product contract
----------------------------------------------------------

D-IMPL-104 records that an aggregate product *"has no representation in this
tree at all"*. That is still true after this module lands.
:class:`ConstituentValidity` is the minimum a caller must state for the
mixing refusal to be computable — an identity, a signal type, and an instant —
and it is deliberately not a product, not a contract element, and not a
declaration. The aggregate-product surface remains unbuilt; only the three
composition rules over it are ruled and now realized.

Two design choices, named as choices
------------------------------------

**1. The N-way anchor is the earliest constituent's, and that is a choice.**
:func:`~ccf.peering.admission.union_lineage` is a *pair* function: its
``graph_snapshot_at`` is the **producer's**, because a producer and a consumer
are ordered and the producer's anchor is the one the crossing product was
assembled against. Its own docstring records that order-independence is
therefore *"a law about the two set axes"* only. An N-way composite of
**siblings has no producer**, so whose anchor to keep is genuinely undefined by
that function, and nothing in the algebra decides it. This module takes the
**earliest** — the most conservative anchor, by analogy with the TTL floor —
because a composite must not claim a snapshot fresher than any constituent
actually saw. That is a design choice, not a derivation, and it is stated here
so no reader infers it fell out of the set algebra.

**2. The stalest constituent is a term of** :func:`compose_expiry`, not a
consequence of the configured derivation. D-IMPL-31 makes the derivation
function per-class configuration (``min`` as the reference default *shape*)
under the D-IMPL-38 parameter discipline. A class that configured something
less conservative than ``min`` could otherwise produce exactly the
fresher-labelled composite the same ruling exists to forbid. Making the
stalest constituent a third term of the minimum is what turns *"a composite is
no fresher than its stalest constituent"* into a property of the function
rather than a property of a configuration. Under the reference default the
third term is an identity and changes nothing.

Errors: raised vs returned
--------------------------

Both shapes appear here, on this tree's standing distinction.
:class:`EmptyCompositionError` is **raised**: composing nothing is a broken
deployment — a caller that reached this module with no constituents has a
wiring defect, and a vacuous success would hand back a lineage of nothing and a
product with no provenance at all. :class:`MixingRefusal` is **returned**: a
composite whose constituent breached a floor is a bad *product*, not a broken
deployment, and a refusal returned as data cannot be swallowed by a bare
``except``.

:class:`MixingRefusal` deliberately does **not** derive from
:class:`~ccf.products.gates.GateRefusal`, and this module imports nothing from
:mod:`ccf.products.gates`. The three validation gates remain three
(INV-CH7-46, INV-CH7-47, INV-CH7-52); the mixing refusal is D-IMPL-31's
assembly-time rule, and a verdict that could travel as a gate verdict by
accident would make the count four by accident. The precedent is
:class:`~ccf.products.payload.PayloadSchemaViolation`, which is kept off the
gate hierarchy for the same reason.

This module holds no TTL number, no freshness figure, no signal-type name and
no threshold of any kind. Every value it compares arrives from a Control Plane
artifact or from the caller (CLAUDE.md §11, CINV-01; D-IMPL-38).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta

from ccf.contracts.base import CCFContract
from ccf.peering.admission import union_lineage
from ccf.products.contract import (
    ConstituentValidityFloors,
    MaxTTL,
    ProductLineage,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "ConstituentValidity",
    "EmptyCompositionError",
    "ExpiryDerivation",
    "MixingRefusal",
    "compose_expiry",
    "compose_lineage",
    "refuse_mixing",
]

#: D-IMPL-31's per-class derivation over constituent signal validities, as a
#: type. The ruling names ``min`` as *"the reference default shape"* and puts
#: the choice per class under the D-IMPL-38 parameter discipline, so the SDK
#: supplies the shape and never a class's choice of it.
#:
#: **The declaration does not yet carry this choice.** Neither
#: :class:`~ccf.products.contract.RegisteredProductClass` nor
#: :class:`~ccf.controlplane.artifacts.ProductClassDeclaration` has a
#: derivation field today; a class therefore states its derivation by passing
#: it, and the field belongs on the declaration when the aggregate-product
#: surface D-IMPL-104 defers arrives. Recorded rather than added here, because
#: adding a governance field is a declaration change and this module is a
#: computation.
ExpiryDerivation = Callable[[Sequence[datetime]], datetime]


class EmptyCompositionError(ValueError):
    """Nothing was offered to compose.

    Raised — never returned — on this tree's raised/returned distinction: a
    caller that reached a composition function with no constituents has a
    wiring defect, not a bad product. Treating the empty case as a vacuous
    success would produce a composite with no provenance, no constituent
    validity to floor against, and a mixing check that could never refuse,
    which is the quietest possible way to lose all three limbs at once.
    """


class ConstituentValidity(CCFContract):
    """One constituent's identity, signal type and validity horizon.

    SDK-defined (CLAUDE.md §11; D-IMPL-31 for the rule this feeds, D-IMPL-104
    for why there is no aggregate product around it). This is the minimum
    :func:`refuse_mixing` must be told; it is not a Context Product, not a
    contract element, and not a governance declaration.

    Attributes:
        constituent_id: The caller's own identifier for this constituent, so a
            refusal names *which* one breached rather than only what kind. A
            deployment value the SDK never interprets.
        signal_type: The deployment's signal-type identifier, matched against
            :attr:`~ccf.products.contract.ConstituentValidityFloors.min_validity_seconds_by_signal`
            structurally and interpreted nowhere.
        expires_at: The instant this constituent's own validity runs out.
    """

    constituent_id: str
    signal_type: str
    expires_at: datetime


class MixingRefusal(CCFContract):
    """D-IMPL-31: a load-bearing constituent breached its declared floor.

    Returned, not raised, and not a :class:`~ccf.products.gates.GateRefusal` —
    see the module docstring for both reasons.

    Carries **both sides** of the failed comparison, on the refusal discipline
    :class:`~ccf.products.gates.LineageMismatchRefusal` and
    :class:`~ccf.peering.admission.PolicyBindingRefusal` hold: the caller
    re-derives neither the constituent's remaining validity nor the floor it
    fell under.

    **Remaining validity is carried as its two instants rather than as a
    duration.** ``expires_at - evaluated_at`` is exact in ``timedelta``
    arithmetic; a seconds figure alongside them would be a float on a value
    that can reach the replay record, and this tree already refuses that
    trade (``src/ccf/halflife/debt.py``: *"these values reach the replay
    record, and floats are not bit-stable"*).

    Attributes:
        constituent_id: The breaching constituent, by the caller's own
            identifier.
        signal_type: Its signal type — which is also *why* it was load-bearing,
            since a floor is declared per signal type and a type with no
            declared floor is not checked at all.
        constituent_expires_at: When that constituent's validity runs out.
        evaluated_at: The instant the mix was evaluated against.
        floor_seconds: The least remaining validity the class declared for
            that signal type.
        detail: Human-readable statement for an operator reading a log. The
            typed fields above are the machine-readable version; nothing
            should parse this string.
    """

    constituent_id: str
    signal_type: str
    constituent_expires_at: datetime
    evaluated_at: datetime
    floor_seconds: int
    detail: str


def compose_lineage(lineages: Sequence[ProductLineage]) -> ProductLineage:
    """Union N constituents' lineage; keep the earliest anchor (D-14, D-IMPL-31).

    CLAUDE.md §7.2 makes lineage continuity a set-union rule, so every
    constituent's ``operators_invoked`` and ``policy_bundle_versions`` entry
    survives into the composite and none is replaced. The union itself is
    :func:`~ccf.peering.admission.union_lineage`, folded pairwise, rather than
    a second union written here: a second union in the tree would be a second
    reading of what lineage continuity means, and the shipped one is already
    property-tested.

    On exactly two constituents this **agrees with**
    :func:`~ccf.peering.admission.union_lineage` on the two set axes, so the
    pairwise case has one behaviour and not two. It deliberately differs on
    ``graph_snapshot_at``: that function keeps the *producer's* anchor because
    a producer and a consumer are ordered, and siblings are not. See the module
    docstring for why the earliest anchor is a choice.

    Args:
        lineages: One :class:`~ccf.products.contract.ProductLineage` per
            constituent. Order is not significant on either set axis.

    Returns:
        The composed lineage: both set axes unioned, anchored at the earliest
        constituent's ``graph_snapshot_at``.

    Raises:
        EmptyCompositionError: no constituents were offered.
    """
    if not lineages:
        raise EmptyCompositionError(
            "cannot compose a lineage from zero constituents: a composite with"
            " no constituent has no provenance, and returning an empty lineage"
            " would report that as a successful composition (D-14)"
        )
    folded = functools.reduce(
        lambda accumulated, nxt: union_lineage(
            producer=nxt, consumer=accumulated
        ),
        lineages[1:],
        lineages[0],
    )
    return ProductLineage(
        operators_invoked=folded.operators_invoked,
        policy_bundle_versions=folded.policy_bundle_versions,
        graph_snapshot_at=min(lineage.graph_snapshot_at for lineage in lineages),
    )


def compose_expiry(
    *,
    constituent_validities: Sequence[datetime],
    max_ttl: MaxTTL,
    ttl_anchor_at: datetime,
    derivation: ExpiryDerivation = min,
) -> datetime:
    """D-IMPL-31's TTL floor: a composite is no fresher than its stalest part.

    The ruled formula is ``min(class MAX_TTL ceiling, derivation over
    constituent signal validities)``. The ceiling is computed here from the
    class's :class:`~ccf.products.contract.MaxTTL` artifact and the anchor the
    caller resolved from the class's
    :data:`~ccf.products.contract.TTLAnchor` — no TTL number is stated in this
    module (D-IMPL-39, CINV-01).

    A **third term**, the stalest constituent's own validity, is part of the
    minimum. Under the reference default derivation it is an identity; under a
    less conservative one it is what keeps the composite from being labelled
    fresher than the constituent that ages out first, which is the outcome
    D-IMPL-31 exists to forbid. This is stated as a property of the function
    rather than left to a class's configuration — see the module docstring.

    Args:
        constituent_validities: Each constituent's own expiry instant.
        max_ttl: The class's registered ceiling artifact.
        ttl_anchor_at: The instant the class's TTL anchor resolved to.
        derivation: The class's declared derivation over constituent
            validities. Defaults to the ruled reference shape.

    Returns:
        The composite's ``expires_at``.

    Raises:
        EmptyCompositionError: no constituent validities were offered.
    """
    if not constituent_validities:
        raise EmptyCompositionError(
            "cannot compose an expiry from zero constituent validities: there"
            " is nothing for the derivation to range over, and falling back to"
            " the class ceiling would label a composite with a freshness no"
            " constituent supports (D-IMPL-31)"
        )
    ceiling = ttl_anchor_at + timedelta(seconds=max_ttl.seconds)
    return min(
        ceiling,
        derivation(constituent_validities),
        min(constituent_validities),
    )


def refuse_mixing(
    *,
    constituents: Sequence[ConstituentValidity],
    floors: ConstituentValidityFloors,
    evaluated_at: datetime,
) -> MixingRefusal | None:
    """D-IMPL-31's mixing-refusal rule, at the moment the mix exists.

    Whitepaper §6.4 Lifecycle Step 4 refuses to assemble a product that
    silently mixes signals of incompatible currency. A class states which
    constituents that applies to by declaring a floor for their signal type in
    :class:`~ccf.products.contract.ConstituentValidityFloors`.

    **Load-bearing is expressed by the floor, not by a flag.** A constituent
    whose signal type has no declared floor is not checked, because
    :data:`~ccf.products.contract.NO_VALIDITY_FLOORS` is the positive
    assertion *no constituent of this class is load-bearing enough to refuse
    assembly on its staleness alone*. Adding a second way to say the same thing
    would let the two disagree.

    **One refusal, deterministically chosen.** The first breach in the
    caller's own constituent order is returned, on the
    :class:`~ccf.products.gates.AttestationRefusal` posture — a breach is a
    per-constituent fact, not an aggregate — and the choice is deterministic in
    the input, which is what replay needs.

    Args:
        constituents: The constituents of the candidate composite.
        floors: The class's declared floors.
        evaluated_at: The instant remaining validity is measured from.

    Returns:
        A :class:`MixingRefusal` for the first constituent whose remaining
        validity falls below its declared floor, or ``None`` when every
        load-bearing constituent still meets it.

    Raises:
        EmptyCompositionError: no constituents were offered. A mix of nothing
            is not a legal mix that happens to pass.
    """
    if not constituents:
        raise EmptyCompositionError(
            "cannot check a mix of zero constituents: a check that cannot"
            " refuse is not a check, and returning None here would report an"
            " empty composite as legally mixed (D-IMPL-31)"
        )
    declared = floors.min_validity_seconds_by_signal
    for constituent in constituents:
        floor_seconds = declared.get(constituent.signal_type)
        if floor_seconds is None:
            continue
        remaining = constituent.expires_at - evaluated_at
        if remaining >= timedelta(seconds=floor_seconds):
            continue
        return MixingRefusal(
            constituent_id=constituent.constituent_id,
            signal_type=constituent.signal_type,
            constituent_expires_at=constituent.expires_at,
            evaluated_at=evaluated_at,
            floor_seconds=floor_seconds,
            detail=(
                f"constituent {constituent.constituent_id!r} of signal type"
                f" {constituent.signal_type!r} expires at"
                f" {constituent.expires_at.isoformat()}, leaving less than the"
                f" declared floor of {floor_seconds}s remaining at"
                f" {evaluated_at.isoformat()}; assembling would label the"
                " composite fresher than its stalest load-bearing constituent"
                " (D-IMPL-31)"
            ),
        )
    return None
