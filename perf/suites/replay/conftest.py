"""Replay-at-scale fixtures (Phase 11 D-16/D-21/D-30; PERF-03).

Two session-scoped pieces feed ``test_replay_scale.py``:

* **One recorded decision against a real fabric.** ``recorded_decision``
  runs the full four-category operator chain + projection + L6 gates against
  the session ``fabric_1k`` fixture (``perf/conftest.py`` — real L1→L2
  ingestion of the seeded rung), builds the five-dimension
  ``DecisionReplayRecord``, and constructs the deployment-side
  ``ReplayEnvironment`` from the same perf artifacts — the example 06
  resolution flow, against the perf battery's neutral domain.

* **A per-rung decision history in a file-backed ArtifactStore.**
  ``history_store_factory(n)`` returns a store holding ``n`` decision-history
  records from ``perf.synth.generator.decision_stream`` (D-30 — every record
  references a real generated entity URI) plus the ONE canonical replay
  record, served through the public ``ReplayWriter`` path. Population cost is
  paid once per rung (session cache), so the timed callable in the test sees
  only the replay itself.

**Population fast path (documented, deliberate).** History records are laid
down as content-addressed files in the store root — the exact on-disk format
``FileArtifactStore.put`` produces (canonical bytes at their content-hash
filename, temp-write + rename) — via a bulk writer, because ``put``'s
per-call naming-index rewrite is O(total-index) per put and therefore
O(n²) across a 100k-record population. The *timed* path touches only the
public store surface (``get`` by content address inside ``replay``); nothing
about the measurement uses the fast path (threat T-11-11: the byte-exact
reproduction assert precedes every timing).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
for _root in (_REPO_ROOT / "src", _REPO_ROOT / "runtime"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from ccf.artifacts.file_store import FileArtifactStore  # noqa: E402
from ccf.contracts.canonical import canonical_bytes, content_hash  # noqa: E402
from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: E402
from ccf.graph.protocols import GraphReader  # noqa: E402
from ccf.products.contract import (  # noqa: E402
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates  # noqa: E402
from ccf.projection.engine import (  # noqa: E402
    OperatorRegistry,
    ProjectionEngine,
)
from ccf.projection.plan import Perspective, ProjectionOutput  # noqa: E402
from ccf.replay.record import (  # noqa: E402
    DecisionReplayRecord,
    PolicyBinding,
    build_replay_record,
)
from ccf.replay.serve import ReplayWriter  # noqa: E402

from perf.suites.common import (  # noqa: E402
    PerfPanelPlan,
    build_operators,
    instant as _instant,
    load_artifact as _load,
)
from perf.synth.generator import decision_stream  # noqa: E402

#: Which generator rung backs the recorded decision's fabric. One small,
#: real fabric for every ladder rung: the variable under measurement is the
#: decision-HISTORY size, so the graph substrate is held constant.
FABRIC_RUNG = 1_000

#: The generator rung whose ``decision_stream`` seeds the history records.
#: 100_000 yields 10_000 base records (D-30's one-per-ten-entities); larger
#: ladder rungs replicate them deterministically (see the D-07 flex note in
#: ``test_replay_scale.py``).
HISTORY_SOURCE_RUNG = 100_000


class PerfReplayEnvironment:
    """The deployment side of the replay seam, from the perf artifacts."""

    def __init__(
        self,
        *,
        control: Any,
        ontology: Any,
        reader: GraphReader,
        policy_version: str,
        now: datetime,
    ) -> None:
        self._control = control
        self._ontology = ontology
        self._reader = reader
        self._policy_version = policy_version
        self._now = now

    def _registry(self) -> OperatorRegistry:
        return build_operators(
            control=self._control,
            ontology=self._ontology,
            reader=self._reader,
            policy_version=self._policy_version,
        )

    def resolve_plan(self, *, plan_id: str) -> Any:
        declared = self._control["product_class"]
        if plan_id != declared["plan_id"]:
            raise LookupError(plan_id)
        return PerfPanelPlan(
            plan_id=declared["plan_id"], required=self._registry().keys()
        )

    def resolve_operators(
        self, *, operator_keys: tuple[str, ...]
    ) -> OperatorRegistry:
        return self._registry()

    def rehydrate_product(
        self, *, record: DecisionReplayRecord, projection: ProjectionOutput
    ) -> ContextProductContract:
        declared = self._control["product_class"]
        return ContextProductContract(
            schema_name=declared["schema_name"],
            schema_version=declared["schema_version"],
            plan_id=projection.plan_id,
            tenant_id=record.tenant_id,
            temporal_boundary=record.context_fabric_snapshot.temporal_boundary,
            expires_at=self._now
            + timedelta(seconds=declared["product_ttl_seconds"]),
            ttl_anchor=declared["ttl_anchor"],
            lineage=ProductLineage(
                operators_invoked=frozenset(
                    record.content_generation_path.operator_plan
                ),
                policy_bundle_versions=frozenset(
                    binding.version
                    for binding in record.policy_bindings.bindings
                ),
                graph_snapshot_at=record.context_fabric_snapshot.temporal_boundary,
            ),
            # Read back off dimension 5, never re-assessed: `debt` is inside
            # the product's content address (D-IMPL-100).
            payload=projection.payload,
            debt=record.content_generation_path.debt,
            # And what that debt pointed at, for a harder reason (D-IMPL-118):
            # the carrier is a top-level vessel field, so `(record, projection)`
            # names it nowhere else and omitting it diverges every replay.
            debt_evidence=record.content_generation_path.debt_evidence,
            # And when its sources last published, for the same reason again
            # (D-IMPL-117 gap 2): the second Track B member takes the same
            # top-level placement, so dimension 5 is the only place a
            # `(record, projection)` rehydrator can read it back from.
            source_refresh_recency=(
                record.content_generation_path.source_refresh_recency
            ),
        )


@dataclass(frozen=True)
class RecordedDecision:
    """Everything replay needs, plus the original to assert bytes against."""

    tenant_id: str
    registry: ControlPlaneRegistry
    reader: GraphReader
    environment: PerfReplayEnvironment
    record: DecisionReplayRecord
    replay_record_class: str
    original_product: ContextProductContract


@pytest.fixture(scope="session")
def recorded_decision(fabric_1k: Any) -> RecordedDecision:
    """One real decision against the session rung-1k fabric, recorded."""
    ontology = _load("ontology.yaml")
    control = _load("controlplane.yaml")
    tenant_id: str = ontology["tenant_id"]
    keys = control["keys"]
    boundary = _instant(control["decision"]["temporal_boundary"])
    now = _instant(control["decision"]["now"])

    registry = fabric_1k.registry
    policy_version = content_hash(control["policy_bundle"])

    operators = build_operators(
        control=control,
        ontology=ontology,
        reader=fabric_1k.reader,
        policy_version=policy_version,
    )
    declared_class = control["product_class"]
    plan = PerfPanelPlan(
        plan_id=declared_class["plan_id"], required=operators.keys()
    )
    perspective = Perspective(
        principal_id=control["perspective"]["principal_id"],
        role=control["perspective"]["role"],
    )
    execution = ProjectionEngine(
        reader=fabric_1k.reader, registry=operators
    ).execute(
        plan=plan,
        perspective=perspective,
        tenant_id=tenant_id,
        temporal_boundary=boundary,
    )
    max_ttl_version = registry.register(
        keys["max_ttl"], MaxTTL(seconds=control["max_ttl_seconds"])
    )
    product_class = register_product_class(
        registry=registry,
        schema_name=declared_class["schema_name"],
        schema_version=declared_class["schema_version"],
        ttl_anchor=declared_class["ttl_anchor"],
        assembly_mode=declared_class["assembly_mode"],
        max_ttl_key=keys["max_ttl"],
        max_ttl_version=max_ttl_version,
    )
    candidate = ContextProductContract(
        schema_name=product_class.schema_name,
        schema_version=product_class.schema_version,
        plan_id=execution.plan_id,
        tenant_id=tenant_id,
        temporal_boundary=boundary,
        expires_at=now
        + timedelta(seconds=declared_class["product_ttl_seconds"]),
        ttl_anchor=product_class.ttl_anchor,
        lineage=ProductLineage(
            operators_invoked=execution.operators_invoked,
            policy_bundle_versions=frozenset({policy_version}),
            graph_snapshot_at=boundary,
        ),
        payload=execution.projection.payload,
    )
    gated = run_gates(
        candidate,
        engine_resolved=execution.operators_invoked,
        now=now,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(gated, ServableProduct), gated

    record = build_replay_record(
        execution=execution,
        product=gated.product,
        perspective=perspective,
        policy_bindings=(
            PolicyBinding(key=keys["policy_bundle"], version=policy_version),
        ),
        assembly_mode=declared_class["assembly_mode"],
        recorded_at=now,
    )
    return RecordedDecision(
        tenant_id=tenant_id,
        registry=registry,
        reader=fabric_1k.reader,
        environment=PerfReplayEnvironment(
            control=control,
            ontology=ontology,
            reader=fabric_1k.reader,
            policy_version=policy_version,
            now=now,
        ),
        record=record,
        replay_record_class=control["artifacts"]["replay_record_class"],
        original_product=gated.product,
    )


def _bulk_write(store: FileArtifactStore, artifact: object) -> str:
    """Lay one artifact down in the store's own on-disk format, no index.

    Byte-identical to what ``FileArtifactStore.put`` writes (canonical bytes
    at the content-hash filename, temp-write + rename); skipped is only the
    O(index) naming-index rewrite, which a 100k-record population turns
    quadratic. Public ``store.get``/``store.exists`` resolve these normally.
    """
    payload = canonical_bytes(artifact)
    address = content_hash(artifact)
    target = store.root / address
    if not target.exists():
        staging = target.with_name(f".{address}.{os.getpid()}.partial")
        staging.write_bytes(payload)
        staging.replace(target)
    return address


class PopulatedStore:
    """One rung's history store: the store, the record address, the count."""

    def __init__(
        self, *, store: FileArtifactStore, record_address: str, count: int
    ) -> None:
        self.store = store
        self.record_address = record_address
        self.count = count


@pytest.fixture(scope="session")
def history_store_factory(
    recorded_decision: RecordedDecision,
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[[int], PopulatedStore]:
    """Session cache of per-rung populated stores.

    ``factory(n)`` → a ``FileArtifactStore`` holding ``n`` decision-history
    records (base records from ``decision_stream(HISTORY_SOURCE_RUNG)``,
    replicated deterministically with a replica index when ``n`` exceeds the
    base count) plus the canonical replay record, served through the public
    ``ReplayWriter`` path so the timed replay resolves it exactly as a
    deployment would.
    """
    base = decision_stream(HISTORY_SOURCE_RUNG)
    cache: dict[int, PopulatedStore] = {}

    def factory(count: int) -> PopulatedStore:
        if count in cache:
            return cache[count]
        control = _load("controlplane.yaml")
        store = FileArtifactStore(
            root=tmp_path_factory.mktemp("perf-replay") / f"store-{count}"
        )
        written = 0
        replica = 0
        while written < count:
            for entry in base:
                if written >= count:
                    break
                record = (
                    entry
                    if replica == 0
                    else {**entry, "decision_id": f"{entry['decision_id']}-r{replica}"}
                )
                _bulk_write(store, record)
                written += 1
            replica += 1
        capability = ReplayWriter(
            store=store,
            artifact_class=control["artifacts"]["replay_record_class"],
        ).write_replay_record(record=recorded_decision.record)
        populated = PopulatedStore(
            store=store,
            record_address=capability.replay_ref.content_address,
            count=count,
        )
        cache[count] = populated
        return populated

    return factory
