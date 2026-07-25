"""Slice contract-subset tests: claims, envelope, ingress Protocol (D-05).

Covers `ccf.contracts.claims` (DESIGN.md §2A.5.1 bitemporal T axis and
append-only L axis), `ccf.signal.envelope` (DESIGN.md §2A.2.1, D-IMPL-33) and
`ccf.signal.source` (DESIGN.md §2A.2.2).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ccf.contracts.canonical import canonical_bytes
from ccf.contracts.claims import (
    EntityClaim,
    LineageEntry,
    PassageAnchor,
    RelationshipClaim,
)
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from ccf.signal.source import SignalSourceProtocol

_T0 = datetime(2026, 7, 25, 12, 0, 0, tzinfo=UTC)


def _source() -> SourceIdentity:
    return SourceIdentity(system_id="src-a")


def _lineage() -> LineageEntry:
    return LineageEntry(
        source=_source(),
        envelope_id="env-1",
        observed_at=_T0,
        passage_anchor=PassageAnchor(kind="paragraph", locator="p/1"),
    )


# --- SignalEnvelope --------------------------------------------------------


def test_envelope_constructs_with_required_fields() -> None:
    envelope = SignalEnvelope(
        tenant_id="t1",
        envelope_id="env-1",
        source=_source(),
        ingestion_timestamp=_T0,
        raw_payload={"k": "v"},
    )
    assert envelope.observed_time is None
    assert envelope.source_metadata == {}


def test_envelope_requires_tenant_id() -> None:
    with pytest.raises(ValidationError):
        SignalEnvelope(  # type: ignore[call-arg]
            envelope_id="env-1",
            source=_source(),
            ingestion_timestamp=_T0,
            raw_payload={},
        )


def test_envelope_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        SignalEnvelope(  # type: ignore[call-arg]
            tenant_id="t1",
            envelope_id="env-1",
            source=_source(),
            ingestion_timestamp=_T0,
            raw_payload={},
            interpreted_entity="acme",
        )


def test_envelope_is_canonically_serializable() -> None:
    envelope = SignalEnvelope(
        tenant_id="t1",
        envelope_id="env-1",
        source=_source(),
        ingestion_timestamp=_T0,
        raw_payload={"b": "2", "a": "1"},
    )
    assert b'"tenant_id":"t1"' in canonical_bytes(envelope)


# --- Claims ----------------------------------------------------------------


def test_entity_claim_requires_full_identity() -> None:
    with pytest.raises(ValidationError):
        EntityClaim(  # type: ignore[call-arg]
            tenant_id="t1",
            entity_class="counterparty",
            observed_at=_T0,
            valid_from=_T0,
            lineage=frozenset({_lineage()}),
        )


def test_entity_claim_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        EntityClaim(  # type: ignore[call-arg]
            tenant_id="t1",
            entity_uri="counterparty://abc",
            entity_class="counterparty",
            observed_at=_T0,
            valid_from=_T0,
            lineage=frozenset({_lineage()}),
            confidence="high",
        )


def test_relationship_claim_requires_both_endpoints() -> None:
    with pytest.raises(ValidationError):
        RelationshipClaim(  # type: ignore[call-arg]
            tenant_id="t1",
            relationship_type="guarantees",
            subject_uri="counterparty://abc",
            observed_at=_T0,
            valid_from=_T0,
            lineage=frozenset({_lineage()}),
        )


def test_claims_carry_bitemporal_axis() -> None:
    claim = EntityClaim(
        tenant_id="t1",
        entity_uri="counterparty://abc",
        entity_class="counterparty",
        observed_at=_T0,
        valid_from=_T0,
        lineage=frozenset({_lineage()}),
    )
    assert claim.valid_to is None
    assert claim.observed_at == _T0
    assert claim.attributes == {}


def test_lineage_entries_are_hashable_and_set_unionable() -> None:
    # L accumulates by set-union (INV-CH7-17); identity is
    # (source, envelope_id, observed_at, passage_anchor).
    same = {_lineage(), _lineage()}
    assert len(same) == 1
    other = LineageEntry(
        source=SourceIdentity(system_id="src-b"),
        envelope_id="env-2",
        observed_at=_T0,
        passage_anchor=None,
    )
    assert len(frozenset({_lineage()}) | frozenset({other})) == 2


def test_lineage_entry_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        LineageEntry(  # type: ignore[call-arg]
            source=_source(),
            envelope_id="env-1",
            observed_at=_T0,
            weight="0.5",
        )


# --- SignalSourceProtocol --------------------------------------------------


class _Adapter:
    def source_identity(self) -> SourceIdentity:
        return _source()

    def envelopes(self, *, tenant_id: str) -> AsyncIterator[SignalEnvelope]:
        raise NotImplementedError


class _NotAnAdapter:
    def source_identity(self) -> SourceIdentity:
        return _source()


def test_structural_conformance_to_signal_source_protocol() -> None:
    assert isinstance(_Adapter(), SignalSourceProtocol)
    assert not isinstance(_NotAnAdapter(), SignalSourceProtocol)
