"""`D-IMPL-332` — unknown valid-time stays unknown, end to end on the assembly path.

**The principle, in Dave's words:** *"The CCF must never turn 'we learned it at
2 PM' into 'it became true at 2 PM.'"*

``observed_at`` answers *when the fabric learned the claim* and ``valid_from``
answers *when the claim was true in the world*. Until this ruling
:meth:`ccf.assembly.worker.AssemblyWorker._stitch` filled the second from the
first whenever a source supplied no ``observed_time``, and called it a stated
reconciliation rule rather than a default. It was still a substitution, and it
**defeated `D-IMPL-331` from below**: a λ_c row declaring
``decay_basis: valid-from`` read the manufactured instant, reported a
perfectly fresh figure for an observation whose real age nobody knew, and made
:class:`~ccf.halflife.decay.MissingDecayInstant` unreachable through the fabric.

This module asserts the whole chain — envelope → worker → L3 → the reference
scorer's observations → ``freshness`` — rather than any one link, because the
defect lived in the JOIN between two links that were each individually correct.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest

from ccf.controlplane.artifacts import HalfLifeEntry, HalfLifeTable
from ccf.halflife.decay import MissingDecayInstant, freshness
from ccf.products.debt_scorer import AssemblyDebtScorer
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

if TYPE_CHECKING:
    from ccf.deployment.manifest import FabricHandle

TENANT = "tenant-332"
INGESTED_AT = datetime(2026, 6, 17, 18, 5, tzinfo=timezone.utc)
OCCURRED_AT = INGESTED_AT - timedelta(seconds=65100)
HALF_LIFE = 86400


def envelope(*, observed_time: datetime | None) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=TENANT,
        envelope_id="env-332",
        source=SourceIdentity(system_id="core-banking"),
        ingestion_timestamp=INGESTED_AT,
        observed_time=observed_time,
        raw_payload={
            "counterparty_lei": "5493001KJTIIGC8Y1R12",
            "counterparty_name": "Acme Holdings",
            "jurisdiction": "GB",
        },
    )


def table(basis: str) -> HalfLifeTable:
    """A λ_c table calibrating whatever class the fixture's rules mint."""
    return HalfLifeTable(
        semver="1.0.0",
        entries={
            "counterparty": HalfLifeEntry(
                half_life_seconds=HALF_LIFE,
                decay_driver="fixture",
                supersession_event="fixture",
                decay_basis=basis,
            )
        },
    )


def observed(fabric: "FabricHandle", *, observed_time: datetime | None) -> Any:
    """Ingest one envelope and hand back the observation the scorer would score."""
    fabric.worker.ingest(envelope(observed_time=observed_time))
    view = fabric.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    observations = AssemblyDebtScorer._observations(view)
    assert observations, "the fixture ingested nothing, so every assertion below is vacuous"
    return observations[0]


def test_an_unsupplied_valid_time_survives_the_whole_path_as_absent(
    fabric: "FabricHandle",
) -> None:
    """Envelope → worker → L3 → observation, and `None` the whole way.

    Asserted at BOTH ends rather than only at the claim: the defect this closes
    was in the join, and a claim that held `None` while the scorer replaced it
    would satisfy a claim-only assertion and still score wrongly.
    """
    fabric.worker.ingest(envelope(observed_time=None))
    claim = fabric.reader.as_of(tenant_id=TENANT, at=INGESTED_AT).entities[0].claim

    assert claim.valid_from is None, "the fabric manufactured a valid-time"
    assert claim.observed_at == INGESTED_AT, (
        "`observed_at` is unchanged by `D-IMPL-332` and must stay ingestion"
    )

    observation = AssemblyDebtScorer._observations(
        fabric.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    )[0]
    assert observation.valid_from is None
    assert observation.observed_at == INGESTED_AT


def test_observed_at_decay_still_works_without_a_valid_time(
    fabric: "FabricHandle",
) -> None:
    """The default basis is untouched — every existing deployment's path.

    This is the compatibility half. A ruling that made absence fatal everywhere
    would have broken every table written before `D-IMPL-331`, all of which
    declare `observed-at` by silence.
    """
    observation = observed(fabric, observed_time=None)
    later = INGESTED_AT + timedelta(seconds=HALF_LIFE)

    assert freshness(
        observation, now=INGESTED_AT, table=table("observed-at"),
        risk_sensitivity=Decimal(1),
    ) == Decimal(1)
    assert freshness(
        observation, now=later, table=table("observed-at"),
        risk_sensitivity=Decimal(1),
    ) < Decimal(1), "the ingestion-basis curve stopped decaying"


def test_valid_from_decay_refuses_when_the_source_never_said(
    fabric: "FabricHandle",
) -> None:
    """**The reachability this ruling restores.**

    Before `D-IMPL-332` this refusal could not fire through the fabric at all:
    `_stitch` guaranteed a non-null `valid_from`, so a `valid-from` row read a
    manufactured instant and reported perfect freshness. `MissingDecayInstant`
    existed and guarded only the direct-construction path.
    """
    observation = observed(fabric, observed_time=None)

    with pytest.raises(MissingDecayInstant):
        freshness(
            observation, now=INGESTED_AT, table=table("valid-from"),
            risk_sensitivity=Decimal(1),
        )


def test_a_supplied_valid_time_is_preserved_and_decays_from_it(
    fabric: "FabricHandle",
) -> None:
    """The other side of the pair: a source that CAN say is believed.

    The two instants are deliberately 65,100 seconds apart — the cp-09
    measurement — so a fixture where they coincide cannot make this pass.
    """
    observation = observed(fabric, observed_time=OCCURRED_AT)

    assert observation.valid_from == OCCURRED_AT
    assert observation.observed_at == INGESTED_AT

    at_ingestion = freshness(
        observation, now=INGESTED_AT, table=table("observed-at"),
        risk_sensitivity=Decimal(1),
    )
    at_source = freshness(
        observation, now=INGESTED_AT, table=table("valid-from"),
        risk_sensitivity=Decimal(1),
    )
    assert at_ingestion == Decimal(1)
    assert Decimal(0) < at_source < Decimal(1), (
        "a source-supplied valid-time did not reach the curve: the declared"
        " basis is not being read through the assembly path"
    )


def test_an_absent_valid_time_is_not_excluded_by_a_validity_window_read(
    fabric: "FabricHandle",
) -> None:
    """`GQ-09`'s absence limb, and it is the reason this ruling is safe.

    A record that makes no valid-time claim cannot be EXCLUDED by a valid-time
    bound: excluding it would assert *"it was not true then"*, which is as much
    an invention as asserting that it was — and it would silently delete every
    unstamped claim from every `require_valid_at_boundary` read.

    **Behavior-preserving, which is what made `admit` the smallest change.**
    Before `D-IMPL-332` an unsupplied valid-time became ingestion, and
    ingestion is always at or before the boundary for any record that survived
    the `GQ-07` as-of cut — so those records were admitted then and are
    admitted now.
    """
    fabric.worker.ingest(envelope(observed_time=None))
    view = fabric.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)

    assert view.entities, (
        "a claim with no valid-time vanished from an as-of read; `GQ-09`'s"
        " absence limb is not admitting it"
    )
    assert view.entities[0].claim.valid_from is None
