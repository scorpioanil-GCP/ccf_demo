"""15.2-08 — the D-11 replay pin: hash tuple in the record, bytes in the store.

The claims, each pinned by a test that fails if the design is done wrong:

1. **Pins are recorded from execution, in order** (T-15.2-15; `GQ-20` at
   docs/GRAPH_QUERY_SEMANTICS.md:391): a no-Similarity execution's record
   carries exactly one pin; a Similarity-bearing execution's carries two, in
   the order the recording reader observed at the seam; a cap-firing
   execution's carries one AND dimension 2 carries the configured value — the
   record shows what ran.
2. **Replay recomputes and compares** (D-11): a served decision replays under
   the recorded dimension-2 cap and the re-executed pin sequence must equal
   the recorded one; a doctored recorded tuple is caught as
   :class:`~ccf.replay.engine.ReplayDivergence`, never quietly replayed.
3. **The auditor path resolves every pin to literal bytes** (T-15.2-28): the
   query bytes land in the store *before* the record append, the store's
   derived address equals ``content_hash(query)``, and retrieving by a pinned
   hash returns bytes that validate back to the identical ``GraphQuery``.
4. **Historical records survive both extensions** (T-15.2-16, D-IMPL-89): the
   four-case compatibility matrix — neither field, pins only, cap only, both
   — resolves at each case's *stored* content address, and a genuinely
   pre-extension record (the captured ``PRE_CHANGE_CANONICAL`` literal)
   verifies byte-for-byte, which the pre-D-IMPL-89 re-validated-model re-hash
   provably refused.
5. **No telemetry in the record** (T-15.2-13; D-04, D-10's outside-the-record
   commitments): neither the reader counters nor the engine's set-size report
   has a field on any dimension of the record contract.

Every domain value — classes, thresholds, TTLs, the query, the boundary —
comes from ``tests/fixtures/banking/*.yaml`` via the quickstart wiring, the
same reuse discipline as ``tests/projection/test_segmentation.py``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef
from ccf.boot import boot
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphQuery, GraphView
from ccf.products.contract import (
    ContextProductContract,
    ProductLineage,
    RegisteredProductClass,
)
from ccf.products.gates import ServableProduct, run_gates
from ccf.projection.engine import (
    ExecutionResult,
    OperatorRegistry,
    ProjectionEngine,
)
from ccf.projection.plan import Perspective, ProjectionOutput, ProjectionPlan
from ccf.replay.engine import ReplayDivergence, replay, resolve_artifact
from ccf.replay.record import (
    NO_GRAPH_QUERIES,
    ContentGenerationPath,
    ContextFabricSnapshot,
    DecisionReplayRecord,
    HarnessTrace,
    ModelVersionRecord,
    PerspectiveConditioning,
    PolicyBinding,
    PolicyBindingsSnapshot,
    build_replay_record,
)
from ccf.replay.serve import (
    QueryPinMismatch,
    QueryPinWriter,
    ReplayWriter,
    serve,
)

from tests.integration.test_proto_quickstart import (
    CreditExposureSummaryPlan,
    _candidate,
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
    _perspective,
    _plan,
    _post_similarity_survivors,
    _RecordingReader,
)
from tests.replay.test_harness_trace import PRE_CHANGE_CANONICAL

#: The query-bytes artifact class — deployment vocabulary, a *test fixture
#: value* here exactly as ``replay_record_class`` is (the SDK assumes neither).
QUERY_ARTIFACT_CLASS = "ccf.graph-query"


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
        keys["resolution_spec"], _resolution_spec(ontology)
    )
    policy_version = registry.register(
        keys["policy_bundle"], control["policy_bundle"]
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
    return FileArtifactStore(root=tmp_path / "artifacts")


def _execute(
    fabric: _Fabric,
    required: tuple[str, ...],
    *,
    survivor_cap: int | None = None,
    registry: OperatorRegistry | None = None,
) -> ExecutionResult:
    return ProjectionEngine(
        reader=fabric.handle.reader,
        registry=registry if registry is not None else _operators(fabric),
        survivor_cap=survivor_cap,
    ).execute(
        plan=_plan(fabric, required),
        perspective=_perspective(fabric),
        tenant_id=fabric.tenant_id,
        temporal_boundary=fabric.boundary,
    )


def _record_for(
    fabric: _Fabric,
    execution: ExecutionResult,
    product_class: RegisteredProductClass,
) -> tuple[ServableProduct, DecisionReplayRecord]:
    """Gate the candidate and build its record, the deployment way."""
    gated = run_gates(
        _candidate(fabric, execution, product_class),
        engine_resolved=execution.operators_invoked,
        now=fabric.now,
        registry=fabric.registry,
        product_class=product_class,
    )
    assert isinstance(gated, ServableProduct)
    record = build_replay_record(
        execution=execution,
        product=gated.product,
        perspective=_perspective(fabric),
        policy_bindings=(
            PolicyBinding(
                key=fabric.control["keys"]["policy_bundle"],
                version=fabric.policy_version,
            ),
        ),
        assembly_mode=fabric.control["product_class"]["assembly_mode"],
        recorded_at=fabric.now,
    )
    return gated, record


def _serve_decision(
    fabric: _Fabric,
    store: FileArtifactStore,
    required: tuple[str, ...],
    *,
    survivor_cap: int | None = None,
) -> tuple[ExecutionResult, DecisionReplayRecord, str]:
    """The full governed serve path; returns the record's content address."""
    execution = _execute(fabric, required, survivor_cap=survivor_cap)
    product_class = _product_class(fabric)
    gated, record = _record_for(fabric, execution, product_class)
    served = serve(
        product=gated,
        record=record,
        replay_writer=ReplayWriter(
            store=store,
            artifact_class=fabric.control["artifacts"]["replay_record_class"],
        ),
        query_pin_writer=QueryPinWriter(
            store=store, artifact_class=QUERY_ARTIFACT_CLASS
        ),
        executed_queries=execution.executed_queries,
    )
    return execution, record, served.replay_ref.content_address


class _Environment:
    """The deployment side of a banking-fixture replay (the rehydration seam)."""

    def __init__(self, fabric: _Fabric, required: tuple[str, ...]) -> None:
        self._fabric = fabric
        self._required = required

    def resolve_plan(self, *, plan_id: str) -> ProjectionPlan:
        declared = self._fabric.control["product_class"]["plan_id"]
        if plan_id != declared:
            raise LookupError(plan_id)
        return CreditExposureSummaryPlan(plan_id=plan_id, required=self._required)

    def resolve_operators(
        self, *, operator_keys: tuple[str, ...]
    ) -> OperatorRegistry:
        return _operators(self._fabric)

    def rehydrate_product(
        self, *, record: DecisionReplayRecord, projection: ProjectionOutput
    ) -> ContextProductContract:
        fabric = self._fabric
        declared = fabric.control["product_class"]
        return ContextProductContract(
            schema_name=declared["schema_name"],
            schema_version=declared["schema_version"],
            plan_id=projection.plan_id,
            tenant_id=record.tenant_id,
            temporal_boundary=record.context_fabric_snapshot.temporal_boundary,
            expires_at=fabric.now
            + timedelta(seconds=declared["product_ttl_seconds"]),
            ttl_anchor=declared["ttl_anchor"],
            lineage=ProductLineage(
                operators_invoked=frozenset(
                    record.content_generation_path.operator_plan
                ),
                policy_bundle_versions=frozenset(
                    binding.version for binding in record.policy_bindings.bindings
                ),
                graph_snapshot_at=record.context_fabric_snapshot.temporal_boundary,
            ),
            # Read back off dimension 5, never re-assessed: `debt` is inside
            # the product's content address (D-IMPL-100).
            payload=projection.payload,
            debt=record.content_generation_path.debt,
        )


# --- 1. pins are recorded from execution, in order ---------------------------


def test_a_no_similarity_execution_pins_exactly_one_query(
    fabric: _Fabric,
) -> None:
    """One round trip, one pin — equal to the compiled query's own hash."""
    recording = _RecordingReader(fabric.handle.reader)
    execution = ProjectionEngine(
        reader=recording, registry=_operators(fabric)
    ).execute(
        plan=_plan(fabric, NO_SIMILARITY),
        perspective=_perspective(fabric),
        tenant_id=fabric.tenant_id,
        temporal_boundary=fabric.boundary,
    )
    _gated, record = _record_for(fabric, execution, _product_class(fabric))

    assert len(recording.queries) == 1
    pins = record.content_generation_path.graph_query_sequence
    assert pins == (content_hash(recording.queries[0]),)
    assert pins == tuple(content_hash(q) for q in execution.executed_queries)


def test_a_similarity_bearing_execution_pins_two_in_order(
    fabric: _Fabric,
) -> None:
    """The D-IMPL-87 shape: two round trips, two pins, execution order."""
    recording = _RecordingReader(fabric.handle.reader)
    execution = ProjectionEngine(
        reader=recording, registry=_operators(fabric)
    ).execute(
        plan=_plan(fabric, FOUR_OPERATORS),
        perspective=_perspective(fabric),
        tenant_id=fabric.tenant_id,
        temporal_boundary=fabric.boundary,
    )
    _gated, record = _record_for(fabric, execution, _product_class(fabric))

    assert len(recording.queries) == 2
    first, second = recording.queries
    pins = record.content_generation_path.graph_query_sequence
    assert pins == (content_hash(first), content_hash(second))
    # Order is the observation order at the seam, not a set.
    assert pins[0] != pins[1]


def test_the_cap_firing_is_visible_as_one_pin_and_the_dim2_value(
    fabric: _Fabric,
) -> None:
    """D-10: one pin (the dropped round trip) AND the configured value, both
    in the record — the cap's firing is auditable from the record alone."""
    registry = _operators(fabric)
    cap = len(_post_similarity_survivors(fabric, registry)) - 1
    execution = _execute(
        fabric, FOUR_OPERATORS, survivor_cap=cap, registry=registry
    )
    _gated, record = _record_for(fabric, execution, _product_class(fabric))

    assert len(execution.executed_queries) == 1
    assert record.content_generation_path.graph_query_sequence == (
        content_hash(execution.executed_queries[0]),
    )
    assert record.policy_bindings.survivor_cap == cap


def test_an_uncapped_record_asserts_no_cap_configured(fabric: _Fabric) -> None:
    """``None`` is the positive no-cap claim, present in the serialized form."""
    execution = _execute(fabric, NO_SIMILARITY)
    _gated, record = _record_for(fabric, execution, _product_class(fabric))
    assert record.policy_bindings.survivor_cap is None
    assert b'"survivor_cap":null' in canonical_bytes(record)


# --- 2. serve-seam ordering and refusals (T-15.2-28) -------------------------


class _PutRecordingStore:
    """Delegates to a real store, recording each ``put``'s artifact class."""

    def __init__(self, inner: FileArtifactStore) -> None:
        self._inner = inner
        self.put_classes: list[str] = []

    def put(
        self, *, tenant_id: str, artifact_class: str, name: str, artifact: object
    ) -> ArtifactRef:
        self.put_classes.append(artifact_class)
        return self._inner.put(
            tenant_id=tenant_id,
            artifact_class=artifact_class,
            name=name,
            artifact=artifact,
        )

    def get(self, *, content_address: str) -> bytes:
        return self._inner.get(content_address=content_address)

    def exists(self, *, content_address: str) -> bool:
        return self._inner.exists(content_address=content_address)

    def resolve_uri(self, *, uri: str) -> str:
        return self._inner.resolve_uri(uri=uri)


def test_the_query_bytes_land_before_the_record_append(
    fabric: _Fabric, store: FileArtifactStore
) -> None:
    """The two puts are ordered: every query-class put precedes the record put,
    so no moment exists at which an appended record pins unresolvable bytes."""
    execution = _execute(fabric, FOUR_OPERATORS)
    gated, record = _record_for(fabric, execution, _product_class(fabric))
    recording = _PutRecordingStore(store)
    serve(
        product=gated,
        record=record,
        replay_writer=ReplayWriter(
            store=recording,
            artifact_class=fabric.control["artifacts"]["replay_record_class"],
        ),
        query_pin_writer=QueryPinWriter(
            store=recording, artifact_class=QUERY_ARTIFACT_CLASS
        ),
        executed_queries=execution.executed_queries,
    )
    record_class = fabric.control["artifacts"]["replay_record_class"]
    assert recording.put_classes == [
        QUERY_ARTIFACT_CLASS,
        QUERY_ARTIFACT_CLASS,
        record_class,
    ]


def test_a_pin_mismatch_is_refused_before_anything_is_persisted(
    fabric: _Fabric, store: FileArtifactStore
) -> None:
    """The record must pin exactly what the seam persists — element for element."""
    execution = _execute(fabric, FOUR_OPERATORS)
    gated, record = _record_for(fabric, execution, _product_class(fabric))
    recording = _PutRecordingStore(store)
    with pytest.raises(QueryPinMismatch):
        serve(
            product=gated,
            record=record,
            replay_writer=ReplayWriter(
                store=recording,
                artifact_class=fabric.control["artifacts"][
                    "replay_record_class"
                ],
            ),
            query_pin_writer=QueryPinWriter(
                store=recording, artifact_class=QUERY_ARTIFACT_CLASS
            ),
            # Reversed: same queries, wrong order — the pinned sequence is an
            # order, not a set.
            executed_queries=tuple(reversed(execution.executed_queries)),
        )
    assert recording.put_classes == []

    with pytest.raises(QueryPinMismatch):
        serve(
            product=gated,
            record=record,
            replay_writer=ReplayWriter(
                store=recording,
                artifact_class=fabric.control["artifacts"][
                    "replay_record_class"
                ],
            ),
            # Queries handed in with nowhere to persist them.
            executed_queries=execution.executed_queries,
        )
    assert recording.put_classes == []


def test_two_executions_asking_the_same_question_converge_on_one_artifact(
    fabric: _Fabric, store: FileArtifactStore
) -> None:
    """Content addressing: the same question stored twice is one artifact."""
    execution = _execute(fabric, NO_SIMILARITY)
    writer = QueryPinWriter(store=store, artifact_class=QUERY_ARTIFACT_CLASS)
    first = writer.write_query_bytes(
        tenant_id=fabric.tenant_id, queries=execution.executed_queries
    )
    second = writer.write_query_bytes(
        tenant_id=fabric.tenant_id, queries=execution.executed_queries
    )
    assert [ref.content_address for ref in first] == [
        ref.content_address for ref in second
    ]


# --- 3. the auditor path (D-11, T-15.2-28) -----------------------------------


def test_the_auditor_resolves_every_pin_to_the_literal_query_bytes(
    fabric: _Fabric, store: FileArtifactStore
) -> None:
    """A pinned hash retrieves bytes that validate back to the identical query.

    Also the empirical store-address finding, pinned: the store's derived
    content address for a stored ``GraphQuery`` **equals** ``content_hash(q)``
    (both are ``sha256(canonical_bytes(...))``), so the name lane and the
    address lane resolve the same pin.
    """
    execution, record, _address = _serve_decision(
        fabric, store, FOUR_OPERATORS
    )
    pins = record.content_generation_path.graph_query_sequence
    assert len(pins) == 2
    for pin, issued in zip(pins, execution.executed_queries, strict=True):
        raw = store.get(content_address=pin)
        rebuilt = GraphQuery.model_validate_json(raw)
        assert content_hash(rebuilt) == pin
        assert rebuilt == issued
        # The replay plane's own read path resolves it identically.
        assert (
            resolve_artifact(
                store=store, content_address=pin, contract=GraphQuery
            )
            == issued
        )


# --- 4. replay verification (D-11) -------------------------------------------


def test_replay_recomputes_the_pin_sequence_and_verifies(
    fabric: _Fabric, store: FileArtifactStore
) -> None:
    """The served Similarity-bearing decision replays: the re-executed pin
    sequence equals the recorded one and every other check still holds."""
    _execution, record, address = _serve_decision(fabric, store, FOUR_OPERATORS)
    outcome = replay(
        record_address=address,
        store=store,
        reader=fabric.handle.reader,
        control_plane=fabric.registry,
        environment=_Environment(fabric, FOUR_OPERATORS),
    )
    assert outcome.record == record
    assert (
        outcome.product_content_address
        == record.content_generation_path.product_content_address
    )


def test_a_capped_decision_replays_under_the_recorded_cap(
    fabric: _Fabric, store: FileArtifactStore
) -> None:
    """D-10's replay-portability claim, executed: the recorded dimension-2 cap
    is what the replay re-executes under, so the capped decision's single-pin
    sequence reproduces — under the deployment's *current* cap it would not."""
    registry = _operators(fabric)
    cap = len(_post_similarity_survivors(fabric, registry)) - 1
    _execution, record, address = _serve_decision(
        fabric, store, FOUR_OPERATORS, survivor_cap=cap
    )
    assert record.policy_bindings.survivor_cap == cap
    assert len(record.content_generation_path.graph_query_sequence) == 1

    outcome = replay(
        record_address=address,
        store=store,
        reader=fabric.handle.reader,
        control_plane=fabric.registry,
        environment=_Environment(fabric, FOUR_OPERATORS),
    )
    assert outcome.record == record


def test_a_doctored_pin_sequence_is_caught_as_divergence(
    fabric: _Fabric, store: FileArtifactStore
) -> None:
    """A seeded mismatch is reported as non-determinism, never replayed past."""
    _execution, record, _address = _serve_decision(
        fabric, store, FOUR_OPERATORS
    )
    path = record.content_generation_path
    doctored = record.model_copy(
        update={
            "content_generation_path": path.model_copy(
                update={
                    "graph_query_sequence": tuple(
                        reversed(path.graph_query_sequence)
                    )
                }
            )
        }
    )
    doctored_address = store.put(
        tenant_id=doctored.tenant_id,
        artifact_class=fabric.control["artifacts"]["replay_record_class"],
        name="doctored",
        artifact=doctored,
    ).content_address
    with pytest.raises(ReplayDivergence, match="query sequence"):
        replay(
            record_address=doctored_address,
            store=store,
            reader=fabric.handle.reader,
            control_plane=fabric.registry,
            environment=_Environment(fabric, FOUR_OPERATORS),
        )


# --- 5. the compatibility matrix (T-15.2-16, D-IMPL-89) ----------------------


def _stored_verbatim(store: FileArtifactStore, payload: bytes) -> str:
    """File ``payload`` exactly as an older writer stored it; return its address.

    Written straight to the substrate rather than through ``put`` because
    ``put`` canonicalizes through the *current* model — the whole point of
    these cases is bytes a **previous** contract version produced.
    """
    address = hashlib.sha256(payload).hexdigest()
    (store.root / address).write_bytes(payload)
    return address


def _strip(payload: bytes, fragment: bytes) -> bytes:
    """Remove ``fragment`` from ``payload``, asserting it was present and the
    result is still well-formed JSON — the surgery must not silently no-op."""
    assert fragment in payload, fragment
    stripped = payload.replace(fragment, b"")
    json.loads(stripped)
    return stripped


def test_the_four_case_compatibility_matrix(
    fabric: _Fabric, store: FileArtifactStore
) -> None:
    """Every historical shape resolves at its stored address (D-IMPL-89).

    Case (iv) — both fields — is a capped execution's record as stored today.
    Cases (i)–(iii) are its bytes with one or both 15.2-08 fields stripped,
    exactly the bytes the pre-extension contract produced: each resolves at
    the sha256 of its own stored bytes, absent fields rebuild to the
    sentinels, present fields survive verbatim, and resolution is stable
    under re-verification.
    """
    registry = _operators(fabric)
    cap = len(_post_similarity_survivors(fabric, registry)) - 1
    execution = _execute(
        fabric, FOUR_OPERATORS, survivor_cap=cap, registry=registry
    )
    _gated, record = _record_for(fabric, execution, _product_class(fabric))
    (pin,) = record.content_generation_path.graph_query_sequence
    full = canonical_bytes(record)
    pin_fragment = f'"graph_query_sequence":["{pin}"],'.encode()
    cap_fragment = f',"survivor_cap":{cap}'.encode()

    # (iv) both fields — today's writer, resolved through the real store.
    address_iv = store.put(
        tenant_id=record.tenant_id,
        artifact_class="decision-replay-record",
        name="matrix-iv",
        artifact=record,
    ).content_address
    assert address_iv == hashlib.sha256(full).hexdigest()
    resolved_iv = resolve_artifact(
        store=store, content_address=address_iv, contract=DecisionReplayRecord
    )
    assert resolved_iv == record

    # (ii) graph_query_sequence only — a pre-cap-field writer's bytes.
    bytes_ii = _strip(full, cap_fragment)
    resolved_ii = resolve_artifact(
        store=store,
        content_address=_stored_verbatim(store, bytes_ii),
        contract=DecisionReplayRecord,
    )
    assert resolved_ii.content_generation_path.graph_query_sequence == (pin,)
    assert resolved_ii.policy_bindings.survivor_cap is None

    # (iii) survivor_cap only — a pre-pin-field writer's bytes.
    bytes_iii = _strip(full, pin_fragment)
    resolved_iii = resolve_artifact(
        store=store,
        content_address=_stored_verbatim(store, bytes_iii),
        contract=DecisionReplayRecord,
    )
    assert (
        resolved_iii.content_generation_path.graph_query_sequence
        == NO_GRAPH_QUERIES
    )
    assert resolved_iii.policy_bindings.survivor_cap == cap

    # (i) neither field — the pre-15.2-08 contract's bytes.
    bytes_i = _strip(_strip(full, pin_fragment), cap_fragment)
    address_i = _stored_verbatim(store, bytes_i)
    resolved_i = resolve_artifact(
        store=store, content_address=address_i, contract=DecisionReplayRecord
    )
    assert (
        resolved_i.content_generation_path.graph_query_sequence
        == NO_GRAPH_QUERIES
    )
    assert resolved_i.policy_bindings.survivor_cap is None

    # Stability under re-verification: resolving again yields the same value.
    assert (
        resolve_artifact(
            store=store, content_address=address_i, contract=DecisionReplayRecord
        )
        == resolved_i
    )

    # The Pydantic-rebuild claim, stated directly on the stored JSON.
    rebuilt = DecisionReplayRecord.model_validate_json(bytes_i)
    assert rebuilt.content_generation_path.graph_query_sequence == (
        NO_GRAPH_QUERIES
    )
    assert rebuilt.policy_bindings.survivor_cap is None


def test_the_pre_phase_fixture_record_verifies_byte_for_byte(
    store: FileArtifactStore,
) -> None:
    """The D-IMPL-89 regression: a genuinely pre-extension record resolves.

    ``PRE_CHANGE_CANONICAL`` was captured from the pre-I.3 builder — it
    predates ``harness_trace``, ``hitl_actions``, ``workflow_step_sequence``,
    ``graph_query_sequence``, and ``survivor_cap``. Its put-time address is
    the sha256 of its stored bytes (``26cdaded…``, the value the ruling
    quotes); the current model re-derives a *different* hash — which is
    exactly why the pre-D-IMPL-89 re-validated-model re-hash refused it, and
    why byte-first verification is the tamper check.
    """
    address = _stored_verbatim(store, PRE_CHANGE_CANONICAL)
    assert address.startswith("26cdaded112c219b")

    record = resolve_artifact(
        store=store, content_address=address, contract=DecisionReplayRecord
    )
    assert (
        record.content_generation_path.graph_query_sequence == NO_GRAPH_QUERIES
    )
    assert record.policy_bindings.survivor_cap is None
    # The re-derived hash of the rebuilt model differs from the stored
    # address — the false-A5 finding, pinned so the re-hash never comes back.
    assert content_hash(record) != address


def test_both_extensions_land_inside_existing_dimensions() -> None:
    """INV-CH7-80: five dimensions, inviolate — the fields extend, never add."""
    dimensions = set(DecisionReplayRecord.model_fields) - {
        "tenant_id",
        "recorded_at",
    }
    assert len(dimensions) == 5
    assert "graph_query_sequence" not in DecisionReplayRecord.model_fields
    assert "survivor_cap" not in DecisionReplayRecord.model_fields
    assert "graph_query_sequence" in ContentGenerationPath.model_fields
    assert "survivor_cap" in PolicyBindingsSnapshot.model_fields


# --- 6. the no-telemetry pin (T-15.2-13; D-04, D-10) -------------------------


def test_the_record_contract_carries_no_telemetry_field() -> None:
    """Performance is never a replay input.

    Neither the reader's monotonic counters (``translated_answers`` /
    ``fallback_answers``, plan 15.2-05, D-04) nor the engine's per-execution
    set-size report (``last_survivor_set_sizes``, plan 15.2-07, D-10's locked
    sub-clause) has a field on any dimension of the record contract — the
    outside-the-record commitments, pinned by name.
    """
    telemetry = {
        "translated_answers",
        "fallback_answers",
        "last_survivor_set_sizes",
    }
    for contract in (
        DecisionReplayRecord,
        ContextFabricSnapshot,
        PolicyBindingsSnapshot,
        ModelVersionRecord,
        HarnessTrace,
        PerspectiveConditioning,
        ContentGenerationPath,
    ):
        assert not (telemetry & set(contract.model_fields)), contract.__name__
