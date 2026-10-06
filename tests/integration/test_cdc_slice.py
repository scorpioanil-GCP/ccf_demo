"""CDC→G end to end: change events → envelopes → graph, through L2 only (FABR-09).

Whitepaper §8.3 Pattern 1; DESIGN.md §2A.4.1. The question this file answers
per assertion is the D-02 one — *would this catch the invariant being broken?*

=========================================  ===================================
Invariant / requirement                    What would fail here
=========================================  ===================================
single-writer (INV-CH7-10, INV-CH8-05)     the adapter has no writer to hand
                                           out; every claim below arrives via
                                           ``worker.ingest``
create semantics                           a ``c`` event would not become a
                                           readable entity claim
update → supersession (INV-CH7-21)         an update would overwrite in place,
                                           and the prior claim would not be
                                           readable as-of the earlier instant
delete → terminal supersession             a ``d`` event would remove a row;
(INV-CH7-04)                               history would shrink instead of grow
idempotent replay (INV-CH7-16/17)          re-running the same feed would
                                           manufacture claims or lineage
typed rejection (T-04-21)                  a malformed event would be skipped
                                           silently instead of raising
tenant from config (T-04-20)               an event body could name its tenant
=========================================  ===================================

Every domain value — entity classes, column names, identifiers, the change-op
key — comes from ``tests/fixtures/banking/ontology.yaml`` and
``tests/fixtures/banking/cdc_events.jsonl``. Delete the fixtures and this file
has nothing to run (CLAUDE.md §6.4 applied to fixture code).
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.assembly.worker import (
    EntityResolutionRule,
    EntityResolutionSpec,
    RelationshipResolutionRule,
)
from ccf.boot import FabricHandle, boot
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import EntityRecord
from ccf.signal.envelope import SignalEnvelope
from ccf.signal.source import SignalSourceProtocol

from ccf_runtime.cdc.adapter import CDCSourceAdapter
from ccf_runtime.cdc.envelope_map import CDCMappingError, to_envelope
from tests.composition import register_at_composition

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"
CDC_FEED = FIXTURES / "cdc_events.jsonl"

# Deployment vocabulary, and therefore test-side values: the source system this
# feed is captured from, and the payload key the change operation lands under.
# The SDK holds neither (CINV-01).
SYSTEM_ID = "core-banking"
CHANGE_OP_KEY = "cdc_op"

# Control Plane keys for this fabric — also deployment vocabulary.
RESOLUTION_SPEC_KEY = "test/cdc-entity-resolution-spec"
POLICY_BUNDLE_KEY = "test/cdc-policy-bundle"


class _StepClock:
    """A deterministic ingestion clock: one fixed step per envelope.

    Two properties matter and they pull in opposite directions. Ingestion time
    must *advance*, or every claim would share an ``observed_at`` and an as-of
    read could not distinguish the state before an update from the state after
    it. It must also be *reproducible*, or replaying the same feed would mint
    new lineage entries and idempotence would be untestable. A counter from a
    fixed base gives both; the wall clock gives neither.
    """

    def __init__(self, *, base: datetime, step: timedelta) -> None:
        self._base = base
        self._step = step
        self._ticks = 0

    def __call__(self) -> datetime:
        instant = self._base + self._ticks * self._step
        self._ticks += 1
        return instant


def _ontology() -> Any:
    return yaml.safe_load((FIXTURES / "ontology.yaml").read_text(encoding="utf-8"))


def _resolution_spec(ontology: Any) -> EntityResolutionSpec:
    """The fixture ontology, with the change operation declared as an attribute.

    Declaring ``cdc_op`` as an attribute key is what turns the CDC operation
    into graph semantics without L1 interpreting anything and without L2
    learning about CDC: a ``u`` produces a claim whose content differs from its
    predecessor and therefore supersedes it, and a ``d`` produces a terminal
    tombstone claim that supersedes the last live one. No row is ever deleted
    (INV-CH7-04) — a graph DELETE would make replay at T+2 years structurally
    impossible.
    """
    return EntityResolutionSpec(
        semver="1.0.0",
        entity_rules=tuple(
            EntityResolutionRule(
                match_key=rule["match_key"],
                entity_class=rule["entity_class"],
                identity_keys=tuple(rule["identity_keys"]),
                attribute_keys=(*rule.get("attribute_keys", ()), CHANGE_OP_KEY),
                # SEC-023: the fixture's declared classification authority.
                attribute_authorities=rule.get("attribute_authorities", {}),
            )
            for rule in ontology["entity_rules"]
        ),
        relationship_rules=tuple(
            RelationshipResolutionRule(
                relationship_type=rule["relationship_type"],
                subject_entity_class=rule["subject_entity_class"],
                object_entity_class=rule["object_entity_class"],
            )
            for rule in ontology["relationship_rules"]
        ),
    )


@pytest.fixture
def ontology() -> Any:
    return _ontology()


@pytest.fixture
def tenant_id(ontology: Any) -> str:
    result: str = ontology["tenant_id"]
    return result


@pytest.fixture
def fabric(tmp_path: Path, ontology: Any) -> Iterator[FabricHandle]:
    """A fabric booted through the real composition root, as always."""
    registry = ControlPlaneRegistry()
    spec_version = register_at_composition(registry, RESOLUTION_SPEC_KEY, _resolution_spec(ontology))
    policy_version = register_at_composition(registry, POLICY_BUNDLE_KEY, {"regime": "cdc-fixture"})
    handle = boot(
        backend="sqlite",
        connection={"database_path": tmp_path / "cdc.sqlite3"},
        registry=registry,
        resolution_spec_key=RESOLUTION_SPEC_KEY,
        resolution_spec_version=spec_version,
        policy_bundle_key=POLICY_BUNDLE_KEY,
        policy_bundle_version=policy_version,
        tenant_ids=(ontology["tenant_id"],),
    )
    try:
        yield handle
    finally:
        handle.close()


def _adapter() -> CDCSourceAdapter:
    """A fresh adapter over the fixture feed, with a reproducible clock."""
    return CDCSourceAdapter(
        system_id=SYSTEM_ID,
        change_op_key=CHANGE_OP_KEY,
        source_path=CDC_FEED,
        clock=_StepClock(
            base=datetime(2026, 3, 1, 9, 0, tzinfo=UTC), step=timedelta(minutes=1)
        ),
    )


def _drain(adapter: CDCSourceAdapter, *, tenant_id: str) -> tuple[SignalEnvelope, ...]:
    """Run the adapter's async emission to completion.

    ``asyncio.run`` per drain, because the fabric core is synchronous
    (D-IMPL-04(b)): the async surface is ingestion's, not L2's.
    """

    async def collect() -> tuple[SignalEnvelope, ...]:
        return tuple([e async for e in adapter.envelopes(tenant_id=tenant_id)])

    return asyncio.run(collect())


def _ingest_feed(fabric: FabricHandle, *, tenant_id: str) -> tuple[SignalEnvelope, ...]:
    """Drive one pass of the feed through L2 — the only route into L3."""
    envelopes = _drain(_adapter(), tenant_id=tenant_id)
    for envelope in envelopes:
        fabric.worker.ingest(envelope)
    return envelopes


def _uri(fabric: FabricHandle, *, tenant_id: str, entity_class: str) -> str:
    """The single URI of ``entity_class`` in the graph."""
    view = fabric.reader.as_of(tenant_id=tenant_id, at=datetime(2100, 1, 1, tzinfo=UTC))
    uris = {
        record.claim.entity_uri
        for record in view.entities
        if record.claim.entity_class == entity_class
    }
    assert len(uris) == 1, f"expected one {entity_class}, got {sorted(uris)}"
    return uris.pop()


def _history(
    fabric: FabricHandle, *, tenant_id: str, entity_class: str
) -> tuple[EntityRecord, ...]:
    return fabric.reader.entity_history(
        tenant_id=tenant_id,
        entity_uri=_uri(fabric, tenant_id=tenant_id, entity_class=entity_class),
    )


# --- envelope_map unit behaviour -------------------------------------------


def test_envelope_map_normalizes_each_operation(tenant_id: str) -> None:
    """c, u and d all normalize; the op reaches the payload, the image is right."""
    envelopes = _drain(_adapter(), tenant_id=tenant_id)
    ops = [envelope.raw_payload[CHANGE_OP_KEY] for envelope in envelopes]
    assert ops == ["c", "c", "u", "d"]
    # The update carries the *after* image, the delete the *before* image.
    assert envelopes[2].raw_payload["jurisdiction"] == "BE"
    assert envelopes[3].raw_payload["facility_id"] == "FAC-100"
    # Tenant and source identity come from configuration, not the event body.
    assert {envelope.tenant_id for envelope in envelopes} == {tenant_id}
    assert {envelope.source.system_id for envelope in envelopes} == {SYSTEM_ID}
    # observed_time is the transaction commit instant (INV-CH7-14).
    assert envelopes[0].observed_time == datetime(2026, 3, 1, 8, 55, tzinfo=UTC)


def test_envelope_map_is_deterministic(tenant_id: str) -> None:
    """The same feed mapped twice yields identical envelope ids."""
    first = _drain(_adapter(), tenant_id=tenant_id)
    second = _drain(_adapter(), tenant_id=tenant_id)
    assert [e.envelope_id for e in first] == [e.envelope_id for e in second]
    assert len({e.envelope_id for e in first}) == len(first)


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param({"op": "z"}, id="unknown-operation"),
        pytest.param(
            {
                "op": "c",
                "source": {"connector": "c", "db": "d", "table": "t"},
                "ts_ms": 1,
            },
            id="missing-after-image",
        ),
        pytest.param(
            {
                "op": "c",
                "source": {"connector": "c", "db": "d", "table": "t"},
                "ts_ms": 1,
                "after": {},
                "unexpected": 1,
            },
            id="unknown-field",
        ),
        pytest.param(["not", "an", "object"], id="not-an-object"),
    ],
)
def test_envelope_map_rejects_malformed_events(raw: object, tenant_id: str) -> None:
    """Malformed events raise a typed error — they are never dropped (T-04-21)."""
    with pytest.raises(CDCMappingError):
        to_envelope(
            raw,
            tenant_id=tenant_id,
            system_id=SYSTEM_ID,
            change_op_key=CHANGE_OP_KEY,
            ingestion_timestamp=datetime(2026, 3, 1, tzinfo=UTC),
        )


def test_envelope_map_refuses_to_shadow_a_source_column(tenant_id: str) -> None:
    """A change-op key that collides with a real column is refused, not merged."""
    raw = {
        "op": "c",
        "source": {"connector": "c", "db": "d", "table": "t"},
        "ts_ms": 1,
        "after": {"status": "open"},
    }
    with pytest.raises(CDCMappingError):
        to_envelope(
            raw,
            tenant_id=tenant_id,
            system_id=SYSTEM_ID,
            change_op_key="status",
            ingestion_timestamp=datetime(2026, 3, 1, tzinfo=UTC),
        )


# --- the adapter's shape ---------------------------------------------------


def test_adapter_conforms_to_the_ingress_seam() -> None:
    """The adapter is a SignalSourceProtocol and holds no graph handle."""
    adapter = _adapter()
    assert isinstance(adapter, SignalSourceProtocol)
    assert adapter.source_identity().system_id == SYSTEM_ID
    # Adapter isolation is a property of the seam's shape (DESIGN.md §2A.2.2).
    assert not any(
        "writer" in name or "reader" in name for name in vars(adapter)
    ), "an ingress adapter must hold neither a GraphWriter nor a GraphReader"


def test_adapter_requires_exactly_one_feed() -> None:
    """Neither feed, or both, is a refusal — never a guess (D-IMPL-38)."""
    with pytest.raises(ValueError):
        CDCSourceAdapter(system_id=SYSTEM_ID, change_op_key=CHANGE_OP_KEY)
    with pytest.raises(ValueError):
        CDCSourceAdapter(
            system_id=SYSTEM_ID,
            change_op_key=CHANGE_OP_KEY,
            source_path=CDC_FEED,
            lines=[],
        )


def test_adapter_reports_the_offending_line(tenant_id: str) -> None:
    """A bad record stops the stream and says where it was."""
    adapter = CDCSourceAdapter(
        system_id=SYSTEM_ID,
        change_op_key=CHANGE_OP_KEY,
        lines=["", "{not json", ""],
    )
    with pytest.raises(CDCMappingError, match="line 2"):
        _drain(adapter, tenant_id=tenant_id)


# --- the slice -------------------------------------------------------------


def test_cdc_create_reaches_the_graph_through_l2(
    fabric: FabricHandle, tenant_id: str
) -> None:
    """Create events land as readable entity claims, written only by L2."""
    _ingest_feed(fabric, tenant_id=tenant_id)
    view = fabric.reader.as_of(tenant_id=tenant_id, at=datetime(2100, 1, 1, tzinfo=UTC))
    classes = {record.claim.entity_class for record in view.entities}
    assert classes == {"counterparty", "facility"}


def test_cdc_update_supersedes_and_prior_state_is_still_readable(
    fabric: FabricHandle, tenant_id: str
) -> None:
    """An update appends a superseding claim; the prior one stays readable as-of."""
    _ingest_feed(fabric, tenant_id=tenant_id)
    history = _history(fabric, tenant_id=tenant_id, entity_class="counterparty")
    assert len(history) == 2
    prior, current = history
    assert prior.claim.attributes["jurisdiction"] == "NL"
    assert current.claim.attributes["jurisdiction"] == "BE"
    assert prior.superseded_by == current.claim_id
    assert prior.superseded_at is not None
    assert current.superseded_by is None

    # An as-of read before the supersession re-renders the earlier state
    # exactly: no future information leaks backwards (INV-CH7-14).
    earlier = fabric.reader.as_of(
        tenant_id=tenant_id, at=prior.claim.observed_at
    )
    jurisdictions = {
        record.claim.attributes["jurisdiction"]
        for record in earlier.entities
        if record.claim.entity_class == "counterparty"
    }
    assert jurisdictions == {"NL"}


def test_cdc_delete_is_terminal_supersession_not_row_removal(
    fabric: FabricHandle, tenant_id: str
) -> None:
    """A delete appends a tombstone claim; nothing is removed from the graph."""
    _ingest_feed(fabric, tenant_id=tenant_id)
    history = _history(fabric, tenant_id=tenant_id, entity_class="facility")
    assert len(history) == 2, "the delete must append, never remove (INV-CH7-04)"
    created, tombstone = history
    assert created.claim.attributes[CHANGE_OP_KEY] == "c"
    assert tombstone.claim.attributes[CHANGE_OP_KEY] == "d"
    assert created.superseded_by == tombstone.claim_id
    assert tombstone.superseded_by is None
    # The node itself is still addressable — the fabric records that the row
    # went away, it does not pretend the row never existed.
    assert created.claim.entity_uri == tombstone.claim.entity_uri


def test_cdc_replay_of_the_same_feed_is_a_no_op(
    fabric: FabricHandle, tenant_id: str
) -> None:
    """Re-running the feed changes neither claims nor lineage (INV-CH7-16/17)."""
    first = _ingest_feed(fabric, tenant_id=tenant_id)
    before = {
        entity_class: _history(fabric, tenant_id=tenant_id, entity_class=entity_class)
        for entity_class in ("counterparty", "facility")
    }

    second = _ingest_feed(fabric, tenant_id=tenant_id)
    assert [e.envelope_id for e in second] == [e.envelope_id for e in first]

    after = {
        entity_class: _history(fabric, tenant_id=tenant_id, entity_class=entity_class)
        for entity_class in ("counterparty", "facility")
    }
    assert after == before, "a replayed CDC feed must not manufacture graph state"
