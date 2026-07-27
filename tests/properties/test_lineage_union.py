"""The lineage set-union law, as a property rather than a round trip (D-14).

CLAUDE.md §7.2: *"Inbound L extends, not replaces, the consumer's L via
set-union; producer's operator plan, graph snapshot, and policy version are all
preserved."* Four laws pin that, over generated inputs:

1. **producer entries survive** admission;
2. **consumer entries survive** admission;
3. **order never matters** on the set axes;
4. **re-admission is idempotent**.

Plus a strict-growth regression guard: over disjoint, non-empty inputs the
result is strictly larger than either side. An implementation that *replaced*
one lineage with the other would satisfy neither survivor law, would fail
order-independence, and would fail strict growth — three of the four laws plus
the guard, which is what makes the failure unmistakable in the report rather
than a single ambiguous red line.

**Why the guard is here at all.** Laws 1 and 2 alone are satisfiable by an
implementation that unions and then *adds* something, and law 4 is satisfiable
by an implementation that returns a constant. Read together with strict growth
they are not. Properties are chosen to be jointly falsifying, not individually
reassuring.

**``graph_snapshot_at`` is single-valued and is therefore not part of the
order-independence law.** It cannot be unioned, and what must be preserved is
the producer's anchor — the instant the product was actually assembled against.
The suite states that as its own law rather than pretending an instant
commutes; see :func:`ccf.a2a.admission.union_lineage`.

Strategies are generated here rather than drawn from the banking fixtures: the
law is about set algebra over lineage, and fixture values would only narrow the
space it is checked over. Concrete banking-shaped cases live in
``tests/a2a/test_admission.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from hypothesis import given
from hypothesis import strategies as st

from ccf.a2a.admission import union_lineage
from ccf.products.contract import ProductLineage

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

    Empty sets are drawable deliberately: a fabric whose union only worked for
    non-empty inputs would pass a suite that never drew one, and the empty case
    is exactly where a "replace when the other side is empty" shortcut hides.
    """
    return ProductLineage(
        operators_invoked=frozenset(draw(st.sets(_TOKENS, max_size=6))),
        policy_bundle_versions=frozenset(draw(st.sets(_TOKENS, max_size=6))),
        graph_snapshot_at=draw(_INSTANTS),
    )


@given(producer=lineages(), consumer=lineages())
def test_producer_entries_always_survive_admission(
    producer: ProductLineage, consumer: ProductLineage
) -> None:
    """Law 1: the producer's provenance is never dropped crossing the boundary."""
    merged = union_lineage(producer=producer, consumer=consumer)
    assert producer.operators_invoked <= merged.operators_invoked
    assert producer.policy_bundle_versions <= merged.policy_bundle_versions


@given(producer=lineages(), consumer=lineages())
def test_consumer_entries_always_survive_admission(
    producer: ProductLineage, consumer: ProductLineage
) -> None:
    """Law 2: admitting a product never erases what the consumer already knew."""
    merged = union_lineage(producer=producer, consumer=consumer)
    assert consumer.operators_invoked <= merged.operators_invoked
    assert consumer.policy_bundle_versions <= merged.policy_bundle_versions


@given(producer=lineages(), consumer=lineages())
def test_the_order_of_the_two_lineages_never_matters(
    producer: ProductLineage, consumer: ProductLineage
) -> None:
    """Law 3: union is commutative on both set axes."""
    forward = union_lineage(producer=producer, consumer=consumer)
    reverse = union_lineage(producer=consumer, consumer=producer)
    assert forward.operators_invoked == reverse.operators_invoked
    assert forward.policy_bundle_versions == reverse.policy_bundle_versions


@given(producer=lineages(), consumer=lineages())
def test_re_admitting_the_same_product_is_idempotent(
    producer: ProductLineage, consumer: ProductLineage
) -> None:
    """Law 4: admitting twice yields the same lineage as admitting once."""
    once = union_lineage(producer=producer, consumer=consumer)
    twice = union_lineage(producer=producer, consumer=once)
    assert twice.operators_invoked == once.operators_invoked
    assert twice.policy_bundle_versions == once.policy_bundle_versions


@given(producer=lineages(), consumer=lineages())
def test_disjoint_non_empty_lineages_grow_strictly(
    producer: ProductLineage, consumer: ProductLineage
) -> None:
    """The regression guard: replacement cannot satisfy strict growth."""
    if not producer.operators_invoked or not consumer.operators_invoked:
        return
    if producer.operators_invoked & consumer.operators_invoked:
        return
    merged = union_lineage(producer=producer, consumer=consumer)
    assert len(merged.operators_invoked) > len(producer.operators_invoked)
    assert len(merged.operators_invoked) > len(consumer.operators_invoked)


@given(producer=lineages(), consumer=lineages())
def test_the_producers_graph_snapshot_anchor_is_preserved(
    producer: ProductLineage, consumer: ProductLineage
) -> None:
    """The single-valued axis: the anchor kept is the one the product was built at."""
    merged = union_lineage(producer=producer, consumer=consumer)
    assert merged.graph_snapshot_at == producer.graph_snapshot_at
