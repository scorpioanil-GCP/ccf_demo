"""15.2-11 — the D-09 dimension-1 attestation pin and the combined matrix.

The claims, each pinned by a test that fails if the design is done wrong:

1. **The attestation in force pins into dimension 1, unconditionally** — a
   new execution against the live graph carries the tier-1
   ``SourceAttestation`` on ``ContextFabricSnapshot.source_attestation``,
   threaded from the engine's own execution facts by
   :func:`~ccf.replay.record.build_replay_record`, present in the canonical
   serialized form (a positive claim, never an omission).
2. **The pin is not identity-bearing** — ``graph_snapshot_id`` stays the
   four D-IMPL-06 constituents exactly, so records written before and after
   the field agree about identical state.
3. **The COMBINED compatibility matrix** (T-15.2-16, D-IMPL-89), now over
   all three 15.2 record extensions — ``graph_query_sequence`` (15.2-08),
   ``survivor_cap`` (15.2-08), ``source_attestation`` (15.2-11): the
   five cases — none of the three, each alone, all three together — each
   canonicalize, resolve at the sha256 of their own stored bytes, stay
   stable under re-verification, and Pydantic rebuild of stored JSON
   lacking any of the fields yields the sentinels.
4. **Pre-phase records survive unmodified** — the captured
   ``PRE_CHANGE_CANONICAL`` literal (which predates every extension) still
   resolves byte-for-byte and rebuilds the ``None`` attestation sentinel.
5. **INV-CH7-80 holds** — the field extends dimension 1; the record itself
   gains nothing.

Every domain value comes from ``tests/fixtures/banking/*.yaml`` via the
quickstart wiring, the same reuse discipline as
``tests/replay/test_query_sequence_pin.py``, whose fixture block and
byte-surgery helpers this module shares.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.boot import boot
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import SourceAttestation
from ccf.replay.engine import resolve_artifact
from ccf.replay.record import (
    NO_GRAPH_QUERIES,
    ContextFabricSnapshot,
    DecisionReplayRecord,
)
from ccf.authz.capability import Register
from tests.controlplane.capabilities import register_capability
from tests.replay.authority import mechanism_put, replay_store

from tests.integration.test_proto_quickstart import (
    _envelopes,
    _Fabric,
    _load,
    _operators,
    _product_class,
    _resolution_spec,
)
from tests.projection.test_segmentation import (
    FOUR_OPERATORS,
    NO_SIMILARITY,
    _post_similarity_survivors,
)
from tests.replay.test_harness_trace import PRE_CHANGE_CANONICAL
from tests.replay.test_query_sequence_pin import (
    _execute,
    _record_for,
    _stored_verbatim,
    _strip,
)

#: The live graph's well-known tier-1 value (D-09) — what BaseGraphReader
#: reports and therefore what every live-graph execution pins.
TIER_1 = SourceAttestation(
    policy_binding="assembly-stamped", lineage="graph-supplied", peer=None
)


# --- fixtures: the booted banking fabric (quickstart wiring, reused) --------


@pytest.fixture(scope="module")
def ontology() -> Any:
    return _load("ontology.yaml")


@pytest.fixture(scope="module")
def control() -> Any:
    return _load("controlplane.yaml")


@pytest.fixture(scope="module")
def events() -> Any:
    return _load("events.yaml")


@pytest.fixture
def fabric(
    tmp_path: Path, ontology: Any, control: Any, events: Any
) -> Iterator[_Fabric]:
    """Boot a fabric from the fixtures and ingest the whole event stream."""
    keys = control["keys"]
    registry = ControlPlaneRegistry()
    spec_version = registry.register(
        register_capability(keys["resolution_spec"], Register), _resolution_spec(ontology)
    )
    policy_version = registry.register(
        register_capability(keys["policy_bundle"], Register), control["policy_bundle"]
    )
    handle = boot(
        backend="sqlite",
        connection={"database_path": tmp_path / "acme-bank.sqlite3"},
        registry=registry,
        resolution_spec_key=keys["resolution_spec"],
        resolution_spec_version=spec_version,
        policy_bundle_key=keys["policy_bundle"],
        policy_bundle_version=policy_version,
    )
    try:
        for envelope in _envelopes(ontology, events):
            handle.worker.ingest(envelope)
        yield _Fabric(
            handle=handle,
            registry=registry,
            policy_version=policy_version,
            ontology=ontology,
            control=control,
        )
    finally:
        handle.close()


@pytest.fixture
def store(tmp_path: Path) -> FileArtifactStore:
    return replay_store(tmp_path / "artifacts", "decision-replay-record")


# --- 1. the pin: recorded from execution, unconditionally --------------------


def test_a_new_executions_record_carries_the_tier1_attestation(
    fabric: _Fabric,
) -> None:
    """The dimension-1 pin, end to end: reader → execution → record."""
    execution = _execute(fabric, NO_SIMILARITY)
    assert execution.source_attestation == TIER_1

    _gated, record = _record_for(fabric, execution, _product_class(fabric))
    assert record.context_fabric_snapshot.source_attestation == TIER_1
    # A positive claim, present in the canonical serialized form.
    assert (
        b'"source_attestation":' + canonical_bytes(TIER_1)
        in canonical_bytes(record)
    )


def test_the_attestation_is_not_identity_bearing(fabric: _Fabric) -> None:
    """``graph_snapshot_id`` stays the four D-IMPL-06 constituents exactly.

    A snapshot built with and without the attestation shares an id — the id
    identifies graph *state*; the attestation is how the source vouched for
    it, pinned beside the id and covered by the record's own content
    address — which is what keeps re-derived ids comparable across records
    written before and after the field existed.
    """
    execution = _execute(fabric, NO_SIMILARITY)
    _gated, record = _record_for(fabric, execution, _product_class(fabric))
    snapshot = record.context_fabric_snapshot

    without = ContextFabricSnapshot.build(
        tenant_id=snapshot.tenant_id,
        temporal_boundary=snapshot.temporal_boundary,
        store_watermark=snapshot.store_watermark,
        touched_entities=snapshot.touched_entities,
        touched_relationships=snapshot.touched_relationships,
    )
    assert without.source_attestation is None
    assert without.graph_snapshot_id == snapshot.graph_snapshot_id


# --- 2. the combined compatibility matrix (T-15.2-16, D-IMPL-89) -------------


def test_the_combined_three_extension_matrix(
    fabric: _Fabric, store: FileArtifactStore
) -> None:
    """Every historical shape over all three 15.2 extensions resolves.

    The full case is a capped Similarity-bearing execution's record as
    stored today — ``graph_query_sequence`` (one pin), ``survivor_cap``
    (the fired cap), and ``source_attestation`` (the tier-1 value) all
    present. The other four cases are its bytes with the fields stripped in
    every combination the extension history could have produced: none of
    the three (a pre-15.2-08 writer), and each alone. Each resolves at the
    sha256 of its own stored bytes, absent fields rebuild to the sentinels,
    present fields survive verbatim, and resolution is stable under
    re-verification.
    """
    registry = _operators(fabric)
    cap = len(_post_similarity_survivors(fabric, registry)) - 1
    execution = _execute(
        fabric, FOUR_OPERATORS, survivor_cap=cap, registry=registry
    )
    _gated, record = _record_for(fabric, execution, _product_class(fabric))

    (pin,) = record.content_generation_path.graph_query_sequence
    attestation = record.context_fabric_snapshot.source_attestation
    assert attestation == TIER_1

    full = canonical_bytes(record)
    pin_fragment = f'"graph_query_sequence":["{pin}"],'.encode()
    cap_fragment = f',"survivor_cap":{cap}'.encode()
    attestation_fragment = (
        b'"source_attestation":' + canonical_bytes(attestation) + b","
    )

    # (all) three fields — today's writer, resolved through the real store.
    address_all = mechanism_put(store, tenant=record.tenant_id, artifact_class="decision-replay-record", name="matrix-all", artifact=record).content_address
    assert address_all == hashlib.sha256(full).hexdigest()
    resolved_all = resolve_artifact(
        store=store, content_address=address_all, contract=DecisionReplayRecord
    )
    assert resolved_all == record

    # (pins alone) — a 15.2-08 writer that predates the cap and attestation
    # fields could not exist (the two 15.2-08 fields landed together), but
    # the shape is still a legal historical hand-off and must resolve.
    bytes_pins = _strip(_strip(full, cap_fragment), attestation_fragment)
    resolved_pins = resolve_artifact(
        store=store,
        content_address=_stored_verbatim(store, bytes_pins),
        contract=DecisionReplayRecord,
    )
    assert resolved_pins.content_generation_path.graph_query_sequence == (pin,)
    assert resolved_pins.policy_bindings.survivor_cap is None
    assert resolved_pins.context_fabric_snapshot.source_attestation is None

    # (cap alone).
    bytes_cap = _strip(_strip(full, pin_fragment), attestation_fragment)
    resolved_cap = resolve_artifact(
        store=store,
        content_address=_stored_verbatim(store, bytes_cap),
        contract=DecisionReplayRecord,
    )
    assert (
        resolved_cap.content_generation_path.graph_query_sequence
        == NO_GRAPH_QUERIES
    )
    assert resolved_cap.policy_bindings.survivor_cap == cap
    assert resolved_cap.context_fabric_snapshot.source_attestation is None

    # (attestation alone) — a 15.2-11 record of an execution that pushed
    # nothing and ran uncapped.
    bytes_attestation = _strip(_strip(full, pin_fragment), cap_fragment)
    resolved_attestation = resolve_artifact(
        store=store,
        content_address=_stored_verbatim(store, bytes_attestation),
        contract=DecisionReplayRecord,
    )
    assert (
        resolved_attestation.content_generation_path.graph_query_sequence
        == NO_GRAPH_QUERIES
    )
    assert resolved_attestation.policy_bindings.survivor_cap is None
    assert (
        resolved_attestation.context_fabric_snapshot.source_attestation
        == attestation
    )

    # (none) — the pre-15.2-08 contract's bytes.
    bytes_none = _strip(
        _strip(_strip(full, pin_fragment), cap_fragment), attestation_fragment
    )
    address_none = _stored_verbatim(store, bytes_none)
    resolved_none = resolve_artifact(
        store=store, content_address=address_none, contract=DecisionReplayRecord
    )
    assert (
        resolved_none.content_generation_path.graph_query_sequence
        == NO_GRAPH_QUERIES
    )
    assert resolved_none.policy_bindings.survivor_cap is None
    assert resolved_none.context_fabric_snapshot.source_attestation is None

    # Stability under re-verification: resolving again yields the same value.
    assert (
        resolve_artifact(
            store=store,
            content_address=address_none,
            contract=DecisionReplayRecord,
        )
        == resolved_none
    )
    assert (
        resolve_artifact(
            store=store,
            content_address=address_all,
            contract=DecisionReplayRecord,
        )
        == resolved_all
    )

    # The Pydantic-rebuild claim, stated directly on the stored JSON.
    rebuilt = DecisionReplayRecord.model_validate_json(bytes_none)
    assert rebuilt.content_generation_path.graph_query_sequence == (
        NO_GRAPH_QUERIES
    )
    assert rebuilt.policy_bindings.survivor_cap is None
    assert rebuilt.context_fabric_snapshot.source_attestation is None


def test_the_pre_phase_fixture_record_still_verifies_byte_for_byte(
    store: FileArtifactStore,
) -> None:
    """The D-IMPL-89 regression, extended to the attestation field.

    ``PRE_CHANGE_CANONICAL`` predates every record extension — including
    ``source_attestation``. It still resolves at the sha256 of its stored
    bytes and rebuilds the ``None`` sentinel: "recorded before source
    attestation existed" is asserted, never inferred.
    """
    address = _stored_verbatim(store, PRE_CHANGE_CANONICAL)
    record = resolve_artifact(
        store=store, content_address=address, contract=DecisionReplayRecord
    )
    assert record.context_fabric_snapshot.source_attestation is None


# --- 3. INV-CH7-80: five dimensions, inviolate -------------------------------


def test_the_attestation_extends_dimension_one_never_the_record() -> None:
    """The field lives on ``ContextFabricSnapshot``; the record gains nothing."""
    dimensions = set(DecisionReplayRecord.model_fields) - {
        "tenant_id",
        "recorded_at",
    }
    assert len(dimensions) == 5
    assert "source_attestation" not in DecisionReplayRecord.model_fields
    assert "source_attestation" in ContextFabricSnapshot.model_fields
