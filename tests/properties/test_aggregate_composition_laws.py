"""The aggregate-composition laws, chosen to be jointly falsifying (D-IMPL-31).

``tests/properties/test_lineage_union.py`` sets the standard this suite is
written to, in its own words: *"Properties are chosen to be jointly falsifying,
not individually reassuring."* Five laws hold over
:mod:`ccf.products.composition`, and each is here because of a specific weaker
implementation it — and only it, or it in company — refuses:

1. **Survivor laws.** Every constituent's ``operators_invoked`` and
   ``policy_bundle_versions`` entries appear in the composite's. *Falsifies* an
   implementation that replaces rather than unions, in either direction, and an
   implementation that keeps only the first or the last constituent.
2. **Order independence on the set axes, and only there.** *Falsifies* an
   implementation that folds asymmetrically — one that let the last constituent
   win a contested axis. It is deliberately **not** extended to
   ``graph_snapshot_at``: that axis is single-valued and the suite does not
   pretend an instant commutes. The anchor gets its own law (5) instead.
3. **Strict growth.** A constituent contributing a new entry strictly grows the
   composite. *Falsifies* what laws 1 and 2 alone cannot: an implementation
   that unions **and then adds** satisfies both survivor laws and order
   independence, and fails here.
4. **Floor monotonicity.** ``compose_expiry`` never returns an expiry later
   than any constituent's. *Falsifies* an implementation returning a constant,
   or the class ceiling, or the *latest* constituent — the last being exactly
   the fresher-labelled composite ``D-IMPL-31`` exists to forbid. It is stated
   over an **arbitrary drawn derivation**, not only the reference default,
   because the stalest constituent is a term of the function rather than a
   consequence of which derivation a class configured.
5. **Refusal completeness.** For *any* constituent set containing a floor
   breach, ``refuse_mixing`` returns a refusal — never ``None``. *Falsifies* a
   refusal that only fires on a hand-picked shape, which is the false green
   this suite exists to prevent; a case-based test cannot reach it, because a
   refusal written against the case it was tested with passes that case by
   construction.
   Its **converse half** is here too — no breach, no refusal — because a
   function that always refused would satisfy the completeness law alone.

Plus the anchor law (the earliest constituent's), which is the single-valued
axis order independence deliberately excludes.

**There is no debt-composition law, and its absence is a ruling, not a gap.**
``docs/DECISIONS.md`` **D-IMPL-104** ruled aggregate debt to be the per-factor
maximum across constituents — worst factor wins — and **deferred the
implementation** until an aggregate-product surface exists to carry it. There
is no ``compose_debt`` to state a law over; the law that belongs here when it
arrives is *the composed debt is never lower than the worst constituent's*, so
an aggregate cannot launder a stale constituent into a confident composite.
:mod:`ccf.products.composition`'s own docstring carries the same citation, so a
reader who notices the missing law finds the reason in either place.

Strategies are generated here rather than drawn from the banking fixtures, on
the lineage suite's reasoning: the laws are about set algebra and instant
ordering, and fixture values would only narrow the space they are checked over.
Concrete worked shapes live in
``tests/products/test_aggregate_composition.py``.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from hypothesis import given
from hypothesis import strategies as st

from ccf.products.composition import (
    ConstituentValidity,
    MixingRefusal,
    compose_expiry,
    compose_lineage,
    refuse_mixing,
)
from ccf.products.contract import (
    ConstituentValidityFloors,
    MaxTTL,
    ProductLineage,
)

# Importing the shared strategies module registers the ``ci`` / ``nightly``
# Hypothesis profiles this suite runs under (04-RESEARCH.md Pitfall 6).
from tests.properties import strategies as _profiles

assert _profiles is not None

_TOKENS = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz.-", min_size=1, max_size=12
)
_INSTANTS = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 1, 1),
).map(lambda value: value.replace(tzinfo=UTC))


@st.composite
def lineages(draw: st.DrawFn) -> ProductLineage:
    """Draw a :class:`ProductLineage`, empty axes included.

    Empty sets are drawable for the reason the lineage suite gives: a fabric
    whose union only worked for non-empty inputs would pass a suite that never
    drew one, and the empty case is where a "replace when the other side is
    empty" shortcut hides.
    """
    return ProductLineage(
        operators_invoked=frozenset(draw(st.sets(_TOKENS, max_size=6))),
        policy_bundle_versions=frozenset(draw(st.sets(_TOKENS, max_size=6))),
        graph_snapshot_at=draw(_INSTANTS),
    )


def constituent_sets() -> st.SearchStrategy[list[ProductLineage]]:
    """One to five constituents — N-way, including the degenerate N of one."""
    return st.lists(lineages(), min_size=1, max_size=5)


@st.composite
def constituents(draw: st.DrawFn) -> ConstituentValidity:
    """Draw one constituent's identity, signal type and validity horizon."""
    return ConstituentValidity(
        constituent_id=draw(_TOKENS),
        signal_type=draw(_TOKENS),
        expires_at=draw(_INSTANTS),
    )


# --------------------------------------------------------------------------
# Laws 1 and 2 — the survivors, and order independence on the set axes
# --------------------------------------------------------------------------


@given(members=constituent_sets())
def test_every_constituents_entries_survive(
    members: Sequence[ProductLineage],
) -> None:
    """Law 1: no constituent's provenance is dropped, whatever N is."""
    composed = compose_lineage(members)
    for member in members:
        assert member.operators_invoked <= composed.operators_invoked
        assert member.policy_bundle_versions <= composed.policy_bundle_versions


@given(members=constituent_sets())
def test_constituent_order_never_matters_on_the_set_axes(
    members: Sequence[ProductLineage],
) -> None:
    """Law 2: siblings are unordered, and the two set axes say so."""
    forward = compose_lineage(list(members))
    reverse = compose_lineage(list(reversed(list(members))))
    assert forward.operators_invoked == reverse.operators_invoked
    assert forward.policy_bundle_versions == reverse.policy_bundle_versions


# --------------------------------------------------------------------------
# Law 3 — strict growth
# --------------------------------------------------------------------------


@given(members=constituent_sets(), newcomer=lineages())
def test_a_constituent_with_a_new_entry_strictly_grows_the_composite(
    members: Sequence[ProductLineage], newcomer: ProductLineage
) -> None:
    """Law 3: union-and-then-add is satisfiable by laws 1 and 2; not by this."""
    without = compose_lineage(list(members))
    contributed = newcomer.operators_invoked - without.operators_invoked
    with_newcomer = compose_lineage([*members, newcomer])
    assert with_newcomer.operators_invoked == (
        without.operators_invoked | newcomer.operators_invoked
    )
    if contributed:
        assert len(with_newcomer.operators_invoked) > len(
            without.operators_invoked
        )
    else:
        assert with_newcomer.operators_invoked == without.operators_invoked


# --------------------------------------------------------------------------
# The single-valued axis — its own law, deliberately not law 2's
# --------------------------------------------------------------------------


@given(members=constituent_sets())
def test_the_composed_anchor_is_the_earliest_constituents(
    members: Sequence[ProductLineage],
) -> None:
    """The N-way anchor rule, held to the choice the module documents."""
    composed = compose_lineage(members)
    assert composed.graph_snapshot_at == min(
        member.graph_snapshot_at for member in members
    )


# --------------------------------------------------------------------------
# Law 4 — floor monotonicity
# --------------------------------------------------------------------------


@given(
    validities=st.lists(_INSTANTS, min_size=1, max_size=5),
    anchor=_INSTANTS,
    ceiling_seconds=st.integers(min_value=0, max_value=1_000_000),
    use_latest=st.booleans(),
)
def test_a_composite_never_expires_later_than_any_constituent(
    validities: Sequence[datetime],
    anchor: datetime,
    ceiling_seconds: int,
    use_latest: bool,
) -> None:
    """Law 4: a constant, the ceiling, or the latest constituent all fail here.

    ``use_latest`` draws the *least* conservative derivation a class could
    configure. The law holds under it, which is the point: the stalest
    constituent is a term of the function, not a consequence of configuration.
    """
    derivation = max if use_latest else min
    composed = compose_expiry(
        constituent_validities=validities,
        max_ttl=MaxTTL(seconds=ceiling_seconds),
        ttl_anchor_at=anchor,
        derivation=derivation,
    )
    assert composed <= min(validities)
    assert composed <= anchor + timedelta(seconds=ceiling_seconds)


# --------------------------------------------------------------------------
# Law 5 — refusal completeness, and its converse half
# --------------------------------------------------------------------------


@given(
    members=st.lists(constituents(), min_size=1, max_size=5),
    floor_seconds=st.integers(min_value=0, max_value=100_000),
    evaluated_at=_INSTANTS,
)
def test_any_floor_breach_anywhere_in_the_set_produces_a_refusal(
    members: Sequence[ConstituentValidity],
    floor_seconds: int,
    evaluated_at: datetime,
) -> None:
    """Law 5: a refusal that fires only on a hand-picked shape fails here."""
    floors = ConstituentValidityFloors(
        min_validity_seconds_by_signal={
            member.signal_type: floor_seconds for member in members
        }
    )
    breached = [
        member
        for member in members
        if member.expires_at - evaluated_at < timedelta(seconds=floor_seconds)
    ]
    refusal = refuse_mixing(
        constituents=members, floors=floors, evaluated_at=evaluated_at
    )
    if breached:
        assert isinstance(refusal, MixingRefusal)
        assert refusal.floor_seconds == floor_seconds
        assert refusal.constituent_id in {
            member.constituent_id for member in breached
        }
    else:
        assert refusal is None


@given(
    members=st.lists(constituents(), min_size=1, max_size=5),
    floor_seconds=st.integers(min_value=0, max_value=100_000),
    evaluated_at=_INSTANTS,
)
def test_a_signal_with_no_declared_floor_is_never_refused_on(
    members: Sequence[ConstituentValidity],
    floor_seconds: int,
    evaluated_at: datetime,
) -> None:
    """Law 5's converse: a function that always refused would fail here.

    Floors are declared for signal types no constituent carries, so nothing in
    the set is load-bearing and no staleness can refuse it — which is what
    ``NO_VALIDITY_FLOORS``' positive assertion means, generalized.
    """
    carried = {member.signal_type for member in members}
    floors = ConstituentValidityFloors(
        min_validity_seconds_by_signal={
            f"{signal}.unheld": floor_seconds for signal in carried
        }
    )
    assert (
        refuse_mixing(
            constituents=members, floors=floors, evaluated_at=evaluated_at
        )
        is None
    )
