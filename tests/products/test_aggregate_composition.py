"""Criterion 8's three limbs, as concrete cases (D-IMPL-31, D-IMPL-104).

Three behaviours are under test here and one deliberately is not:

* **lineage union** across N constituents — :func:`ccf.products.composition.compose_lineage`;
* **the TTL floor** — :func:`ccf.products.composition.compose_expiry`;
* **the mixing refusal** — :func:`ccf.products.composition.refuse_mixing`, the
  implementation of ``D-IMPL-31``'s constituent-validity floors; and
* **not debt composition**, which ``D-IMPL-104`` ruled as to *meaning*
  (worst-factor-wins, the per-factor maximum across constituents) and
  **deferred as to implementation** until an aggregate-product surface exists.
  There is therefore no ``compose_debt`` to test, and its absence is asserted
  here so that a later reader finds the omission stated rather than inferred.

The bind-time freshness-SLA refusal —
:func:`ccf.deployment.binder.refuse_unpromisable_freshness_sla` — is the third
limb and is tested at the bottom of this module, beside the composition cases,
because the two halves of criterion 8 are one commitment split across two
layers.

Generated-strategy laws over the same functions live in
``tests/properties/test_aggregate_composition_laws.py``. These cases pin the
worked shapes; those laws pin the algebra.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from datetime import UTC, datetime, timedelta

import pytest

from ccf.controlplane.artifacts import (
    PRODUCT_CLASS,
    ProductClassDeclaration,
    load_artifact,
)
from ccf.deployment.binder import refuse_unpromisable_freshness_sla
from ccf.peering.admission import union_lineage
from ccf.products import composition
from ccf.products.composition import (
    ConstituentValidity,
    EmptyCompositionError,
    MixingRefusal,
    compose_expiry,
    compose_lineage,
    refuse_mixing,
)
from ccf.products.contract import (
    NO_VALIDITY_FLOORS,
    ConstituentValidityFloors,
    MaxTTL,
    ProductLineage,
)
from ccf.products.gates import GateRefusal

_ANCHOR = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)

#: Fixture vocabulary — a test-side signal-type identifier, never an SDK value
#: (CINV-01). The SDK never interprets one; these tests only need two names it
#: can tell apart.
SIGNAL = "fixture.intraday-blotter"
SLOW_SIGNAL = "fixture.period-financials"


def _lineage(
    operators: set[str], bundles: set[str], anchor: datetime
) -> ProductLineage:
    return ProductLineage(
        operators_invoked=frozenset(operators),
        policy_bundle_versions=frozenset(bundles),
        graph_snapshot_at=anchor,
    )


# --------------------------------------------------------------------------
# Limb 1 — lineage union across N constituents
# --------------------------------------------------------------------------


def test_every_constituents_lineage_entries_survive_composition() -> None:
    """No constituent's provenance is dropped by the composite (D-14)."""
    first = _lineage({"op.a"}, {"bundle.1"}, _ANCHOR)
    second = _lineage({"op.b"}, {"bundle.2"}, _ANCHOR + timedelta(minutes=5))
    third = _lineage({"op.c"}, {"bundle.3"}, _ANCHOR + timedelta(minutes=9))

    composed = compose_lineage([first, second, third])

    assert composed.operators_invoked == frozenset({"op.a", "op.b", "op.c"})
    assert composed.policy_bundle_versions == frozenset(
        {"bundle.1", "bundle.2", "bundle.3"}
    )


def test_constituent_order_does_not_change_the_composed_set_axes() -> None:
    """Siblings are unordered; the two set axes must say so."""
    first = _lineage({"op.a"}, {"bundle.1"}, _ANCHOR)
    second = _lineage({"op.b"}, {"bundle.2"}, _ANCHOR + timedelta(minutes=5))
    third = _lineage({"op.c"}, {"bundle.3"}, _ANCHOR + timedelta(minutes=9))

    forward = compose_lineage([first, second, third])
    reverse = compose_lineage([third, second, first])

    assert forward.operators_invoked == reverse.operators_invoked
    assert forward.policy_bundle_versions == reverse.policy_bundle_versions


def test_the_pairwise_case_agrees_with_union_lineage_on_the_set_axes() -> None:
    """Two constituents have one behaviour, not two."""
    producer = _lineage({"op.a"}, {"bundle.1"}, _ANCHOR)
    consumer = _lineage({"op.b"}, {"bundle.2"}, _ANCHOR + timedelta(minutes=5))

    composed = compose_lineage([producer, consumer])
    merged = union_lineage(producer=producer, consumer=consumer)

    assert composed.operators_invoked == merged.operators_invoked
    assert composed.policy_bundle_versions == merged.policy_bundle_versions


def test_the_composed_anchor_is_the_earliest_constituent_anchor() -> None:
    """The N-way anchor rule: the most conservative anchor, by design choice."""
    earliest = _ANCHOR
    composed = compose_lineage(
        [
            _lineage({"op.a"}, set(), _ANCHOR + timedelta(minutes=9)),
            _lineage({"op.b"}, set(), earliest),
            _lineage({"op.c"}, set(), _ANCHOR + timedelta(minutes=5)),
        ]
    )
    assert composed.graph_snapshot_at == earliest


def test_composing_an_empty_constituent_set_is_refused() -> None:
    """Not a vacuous success: there is no lineage of nothing."""
    with pytest.raises(EmptyCompositionError):
        compose_lineage([])


def test_compose_lineage_reuses_union_lineage_rather_than_re_unioning() -> None:
    """A second union in the tree is a second reading of lineage continuity."""
    source = inspect.getsource(composition)
    assert "union_lineage(" in source
    assert "operators_invoked |" not in source
    assert "policy_bundle_versions |" not in source


# --------------------------------------------------------------------------
# Limb 2 — the TTL floor
# --------------------------------------------------------------------------


def test_the_composite_expires_no_later_than_its_stalest_constituent() -> None:
    """D-IMPL-31's derivation over constituent validities."""
    stalest = _ANCHOR + timedelta(hours=1)
    composed = compose_expiry(
        constituent_validities=[
            _ANCHOR + timedelta(hours=6),
            stalest,
            _ANCHOR + timedelta(hours=3),
        ],
        max_ttl=MaxTTL(seconds=86_400),
        ttl_anchor_at=_ANCHOR,
    )
    assert composed == stalest


def test_the_class_ceiling_binds_when_it_is_earlier_than_every_constituent() -> (
    None
):
    """``min(class MAX_TTL ceiling, derivation …)`` — the ceiling half."""
    composed = compose_expiry(
        constituent_validities=[
            _ANCHOR + timedelta(hours=6),
            _ANCHOR + timedelta(hours=9),
        ],
        max_ttl=MaxTTL(seconds=3_600),
        ttl_anchor_at=_ANCHOR,
    )
    assert composed == _ANCHOR + timedelta(hours=1)


def test_a_less_conservative_derivation_cannot_outrun_the_stalest() -> None:
    """The stalest constituent is a term of the composition, not a hope."""
    stalest = _ANCHOR + timedelta(hours=1)
    composed = compose_expiry(
        constituent_validities=[stalest, _ANCHOR + timedelta(hours=6)],
        max_ttl=MaxTTL(seconds=86_400),
        ttl_anchor_at=_ANCHOR,
        derivation=max,
    )
    assert composed == stalest


def test_composing_an_expiry_from_no_constituents_is_refused() -> None:
    with pytest.raises(EmptyCompositionError):
        compose_expiry(
            constituent_validities=[],
            max_ttl=MaxTTL(seconds=3_600),
            ttl_anchor_at=_ANCHOR,
        )


# --------------------------------------------------------------------------
# Limb 3 — the mixing refusal (D-IMPL-31's constituent-validity floors)
# --------------------------------------------------------------------------


def _constituent(
    identifier: str, signal: str, expires_in: timedelta
) -> ConstituentValidity:
    return ConstituentValidity(
        constituent_id=identifier,
        signal_type=signal,
        expires_at=_ANCHOR + expires_in,
    )


def test_a_constituent_breaching_its_floor_refuses_assembly() -> None:
    """The 90-day/15-minute asymmetry, refused rather than labelled."""
    floors = ConstituentValidityFloors(
        min_validity_seconds_by_signal={SIGNAL: 3_600}
    )
    refusal = refuse_mixing(
        constituents=[
            _constituent("filing", SLOW_SIGNAL, timedelta(days=30)),
            _constituent(
                "blotter", SIGNAL, timedelta(minutes=15)
            ),
        ],
        floors=floors,
        evaluated_at=_ANCHOR,
    )

    assert isinstance(refusal, MixingRefusal)
    assert refusal.constituent_id == "blotter"
    assert refusal.signal_type == SIGNAL
    assert refusal.constituent_expires_at == _ANCHOR + timedelta(minutes=15)
    assert refusal.evaluated_at == _ANCHOR
    assert refusal.floor_seconds == 3_600


def test_a_signal_with_no_declared_floor_is_not_load_bearing() -> None:
    """``NO_VALIDITY_FLOORS`` is a positive assertion, not an omission."""
    assert (
        refuse_mixing(
            constituents=[
                _constituent("blotter", SIGNAL, timedelta(seconds=1))
            ],
            floors=NO_VALIDITY_FLOORS,
            evaluated_at=_ANCHOR,
        )
        is None
    )


def test_constituents_that_meet_their_floors_do_not_refuse() -> None:
    floors = ConstituentValidityFloors(
        min_validity_seconds_by_signal={SIGNAL: 3_600}
    )
    assert (
        refuse_mixing(
            constituents=[
                _constituent("blotter", SIGNAL, timedelta(hours=2))
            ],
            floors=floors,
            evaluated_at=_ANCHOR,
        )
        is None
    )


def test_an_already_expired_constituent_breaches_a_zero_floor() -> None:
    """A floor of zero still asserts *some* remaining validity is required."""
    floors = ConstituentValidityFloors(
        min_validity_seconds_by_signal={SIGNAL: 0}
    )
    refusal = refuse_mixing(
        constituents=[
            _constituent("blotter", SIGNAL, timedelta(minutes=-1))
        ],
        floors=floors,
        evaluated_at=_ANCHOR,
    )
    assert isinstance(refusal, MixingRefusal)


def test_refusing_a_mix_of_no_constituents_is_refused_not_vacuously_clean() -> (
    None
):
    with pytest.raises(EmptyCompositionError):
        refuse_mixing(
            constituents=[],
            floors=NO_VALIDITY_FLOORS,
            evaluated_at=_ANCHOR,
        )


def test_a_mixing_refusal_is_not_a_gate_verdict() -> None:
    """The three validation gates remain three (the payload-schema precedent)."""
    assert not issubclass(MixingRefusal, GateRefusal)


# --------------------------------------------------------------------------
# The debt limb, deliberately absent (D-IMPL-104)
# --------------------------------------------------------------------------


def test_no_debt_composition_ships_and_the_module_says_why() -> None:
    """``D-IMPL-104`` ruled the meaning and deferred the implementation."""
    assert not hasattr(composition, "compose_debt")
    assert composition.__doc__ is not None
    assert "D-IMPL-104" in composition.__doc__


# --------------------------------------------------------------------------
# Limb 3 of criterion 8 — the bind-time freshness-SLA refusal
# --------------------------------------------------------------------------


def _declaration(
    name: str, sla_seconds: int | None = None
) -> ProductClassDeclaration:
    """Parse a ``ccf.product-class`` document through the one supported seam.

    Authored text rather than a constructed model, on the discipline
    ``tests/deployment/test_binder.py`` states: a refusal reachable only by
    constructing two objects says nothing about whether an *author* could ever
    make the two documents disagree. Here the freshness promise is one line of
    one document, so the refusal is reachable by editing a number.
    """
    sla = (
        ""
        if sla_seconds is None
        else (
            "freshness_sla:\n"
            "  max_age_seconds_by_signal:\n"
            f"    {SIGNAL}: {sla_seconds}\n"
        )
    )
    parsed = load_artifact(
        (
            "semver: 1.0.0\n"
            f"schema_name: {name}\n"
            "schema_version: 1.0.0\n"
            "ttl_anchor: from_decision\n"
            "assembly_mode: algorithmic\n"
            "max_ttl_key: tenant-fixture/composition/max-ttl\n"
            "required_operator_keys:\n"
            "- fixture.operator\n"
        )
        + sla,
        PRODUCT_CLASS,
    )
    assert isinstance(parsed, ProductClassDeclaration)
    return parsed


def test_a_promisable_freshness_sla_binds_without_complaint() -> None:
    """The mandatory pair's admitting half: a binder that always refused fails here."""
    assert (
        refuse_unpromisable_freshness_sla(
            declared=_declaration("composite", 3_600),
            constituents=[_declaration("constituent", 900)],
        )
        is None
    )


def test_an_unpromisable_freshness_sla_is_refused_at_bind_time() -> None:
    """The refusing half: a binder that always admitted fails here."""
    with pytest.raises(ValueError) as excinfo:
        refuse_unpromisable_freshness_sla(
            declared=_declaration("composite", 86_400),
            constituents=[_declaration("constituent", 2_592_000)],
        )
    message = str(excinfo.value)
    assert "composite" in message
    assert "constituent" in message
    assert SIGNAL in message
    assert "86400" in message
    assert "2592000" in message


def test_a_constituent_silent_on_a_signal_is_not_read_as_a_weak_promise() -> (
    None
):
    """``UNMEASURED_FRESHNESS_SLA`` measures no signal; it promises nothing weak."""
    assert (
        refuse_unpromisable_freshness_sla(
            declared=_declaration("composite", 3_600),
            constituents=[_declaration("constituent")],
        )
        is None
    )


def test_a_class_declaring_no_sla_of_its_own_promises_nothing_to_breach() -> None:
    assert (
        refuse_unpromisable_freshness_sla(
            declared=_declaration("composite"),
            constituents=[_declaration("constituent", 2_592_000)],
        )
        is None
    )


def test_the_sla_refusal_is_raised_and_never_repaired() -> None:
    """No path hands back a repaired value; every ``return`` is bare."""
    tree = ast.parse(
        textwrap.dedent(inspect.getsource(refuse_unpromisable_freshness_sla))
    )
    returns = [node for node in ast.walk(tree) if isinstance(node, ast.Return)]
    assert returns, "the function must have at least one return path"
    assert all(node.value is None for node in returns)
