"""The replay engine: a recorded decision, reproduced and hash-verified.

Whitepaper §7.10 (every decision forensically reconstructible years later
against the exact fabric state at decision time — INV-CH7-79/86); D-IMPL-06
(logical snapshots); D-IMPL-26 (exact-version artifact resolution); D-IMPL-44
(the re-hydration path); DESIGN.md §2B.5.

The pipeline, in order, with each step's failure mode named:

1. **Resolve the record** at its content address. A missing record is
   :class:`ReplayUnresolvable` — never the nearest one, never the newest under
   the name. The bytes are re-hashed on arrival, so a substrate that returned
   the wrong artifact is caught here rather than believed (T-04-17).
2. **Resolve every Control Plane binding at its exact recorded version.** A
   control plane that has lost the version a decision was made under cannot say
   what that decision saw; that is :class:`ReplayUnresolvable`, not a fallback.
3. **Resolve the projection plan and operators** through the deployment's
   :class:`ReplayEnvironment`. The SDK cannot know a deployment's Π or its
   operator parameters — they are user code and user configuration — so this is
   a seam. It is a *verified* seam: what the environment supplies is checked
   against the record, never trusted.
4. **Re-execute** against a :class:`~ccf.replay.snapshots.SnapshotReader` pinned
   to the recorded tenant and boundary, then check that the executed step
   sequence — operator keys, categories, and parameter hashes, in order —
   equals the recorded one. Drifted parameters surface as
   :class:`ReplayDivergence` here rather than as a quietly different answer.
5. **Check the snapshot id** derived from the re-execution against the recorded
   one. Both are content-derived, so agreement is a statement about state.
6. **Re-hydrate the product** and check its content address against the
   recorded one. This is the claim in one line: *the same bytes*.

**Divergence is raised, not returned.** The gates (L6) return refusals as data
because a caller there holds a candidate it might legitimately discard. A
replay has no such option: a decision that does not reproduce is a finding, and
a caller that could receive it as a value could log it and carry on with the
freshly-computed product — which is precisely the substitution this engine
exists to prevent.

Nothing here reads a clock, and nothing here resolves "latest".

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ccf.artifacts.protocol import ArtifactStoreError, ArtifactStoreProtocol
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol
from ccf.graph.protocols import GraphReader
from ccf.products.contract import ContextProductContract
from ccf.projection.engine import OperatorRegistry, ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionOutput, ProjectionPlan
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.snapshots import SnapshotReader, snapshot_of_execution

__ccf_mode__ = "algorithmic"

__all__ = [
    "ReplayDivergence",
    "ReplayEnvironment",
    "ReplayError",
    "ReplayOutcome",
    "ReplayUnresolvable",
    "replay",
]


class ReplayError(Exception):
    """Base of the replay engine's failures."""


class ReplayUnresolvable(ReplayError, LookupError):
    """Something the record names cannot be resolved at its exact version.

    The record, a Control Plane binding, a projection plan, an operator. In
    every case the engine stops: a replay that substituted a *different*
    version would produce a confident answer about a decision that never
    happened, which is worse than no answer (CLAUDE.md §7.4, D-IMPL-26).
    """


class ReplayDivergence(ReplayError):
    """The reproduction does not match what was recorded.

    A finding, and therefore raised rather than returned — see the module
    docstring. Carries what disagreed in its message so the operator reading it
    can tell parameter drift from state drift from an envelope mismatch.
    """


@runtime_checkable
class ReplayEnvironment(Protocol):
    """The deployment side of a replay (SDK-defined seam).

    A record names *what* ran — plan id, operator keys, parameter hashes — but
    the things themselves are deployment code and deployment configuration. The
    environment supplies them; the engine verifies them. Nothing an environment
    returns is taken on trust: a wrong plan produces a step-sequence mismatch, a
    wrong parameter set produces a parameter-hash mismatch, and a wrong product
    envelope produces a content-address mismatch.
    """

    def resolve_plan(self, *, plan_id: str) -> ProjectionPlan:
        """Return the projection registered under ``plan_id``.

        Raises:
            LookupError: no such plan. The engine translates it into
                :class:`ReplayUnresolvable`.
        """
        ...

    def resolve_operators(self, *, operator_keys: tuple[str, ...]) -> OperatorRegistry:
        """Return a registry holding the recorded operators as they then were.

        ``operator_keys`` is the recorded execution order, passed so an
        environment can resolve historical parameter sets rather than current
        ones.

        Raises:
            LookupError: an operator cannot be reconstituted.
        """
        ...

    def rehydrate_product(
        self, *, record: DecisionReplayRecord, projection: ProjectionOutput
    ) -> ContextProductContract:
        """Rebuild the delivered product from the record and the re-execution.

        The payload comes from the re-executed projection; the envelope
        (schema, TTL anchor, expiry) comes from the deployment's product class.
        The engine checks the result's content address against the record, so
        an envelope reconstructed wrongly is caught rather than accepted.
        """
        ...


class ReplayOutcome(CCFContract):
    """A verified reproduction. Constructed only after every check has passed.

    Holding one of these *is* the evidence — the engine has no path that
    returns an outcome it could not verify, so a caller cannot receive a
    "probably" and read it as a "yes".

    Attributes:
        record: The record that was replayed, resolved at its exact address.
        product: The reproduced product.
        record_content_address: Where the record was resolved from.
        product_content_address: Content address of the reproduced product,
            equal by construction to the one the record carries.
        graph_snapshot_id: Snapshot id derived from the re-execution, equal by
            construction to the recorded one.
    """

    record: DecisionReplayRecord
    product: ContextProductContract
    record_content_address: str
    product_content_address: str
    graph_snapshot_id: str


def _resolve_record(
    *, store: ArtifactStoreProtocol, record_address: str
) -> DecisionReplayRecord:
    try:
        payload = store.get(content_address=record_address)
    except (ArtifactStoreError, KeyError) as missing:
        raise ReplayUnresolvable(
            f"no decision replay record is stored at {record_address!r}; "
            "replay resolves the exact recorded artifact and has no fallback "
            "(CLAUDE.md §7.4, D-IMPL-26)"
        ) from missing
    record = DecisionReplayRecord.model_validate_json(payload)
    reproduced = content_hash(record)
    if reproduced != record_address:
        raise ReplayDivergence(
            f"the artifact at {record_address!r} hashes to {reproduced!r}; the "
            "store returned bytes that are not the record that was asked for"
        )
    return record


def _resolve_bindings(
    *, record: DecisionReplayRecord, control_plane: ControlPlaneProtocol
) -> None:
    """Resolve every recorded binding at its pinned version, or refuse."""
    for binding in record.policy_bindings.bindings:
        try:
            control_plane.resolve(binding.key, binding.version)
        except ControlPlaneMissing as missing:
            raise ReplayUnresolvable(
                f"policy binding ({binding.key!r}, {binding.version!r}) is not "
                "registered; the configuration this decision was made under is "
                "gone and no other version stands in for it (D-IMPL-38)"
            ) from missing


def replay(
    *,
    record_address: str,
    store: ArtifactStoreProtocol,
    reader: GraphReader,
    control_plane: ControlPlaneProtocol,
    environment: ReplayEnvironment,
) -> ReplayOutcome:
    """Reproduce the decision recorded at ``record_address``, exactly.

    Args:
        record_address: Content address of the :class:`DecisionReplayRecord`.
            An address, not a name: names move, addresses do not.
        store: Where the record lives (CLAUDE.md §7.4).
        reader: Live read access to the graph. Scoped to the recorded snapshot
            before anything reads through it.
        control_plane: Where the recorded bindings are resolved at their pinned
            versions.
        environment: The deployment's plan, operators, and product envelope.

    Returns:
        A :class:`ReplayOutcome`, which exists only if every check passed.

    Raises:
        ReplayUnresolvable: the record, a binding, the plan, or an operator
            cannot be resolved at its exact recorded version.
        ReplayDivergence: something resolved but did not reproduce.
    """
    record = _resolve_record(store=store, record_address=record_address)
    _resolve_bindings(record=record, control_plane=control_plane)

    path = record.content_generation_path
    try:
        plan = environment.resolve_plan(plan_id=path.plan_id)
    except LookupError as missing:
        raise ReplayUnresolvable(
            f"projection plan {path.plan_id!r} cannot be resolved; the "
            "interpretation this decision used is not available"
        ) from missing
    try:
        operators = environment.resolve_operators(operator_keys=path.operator_plan)
    except LookupError as missing:
        raise ReplayUnresolvable(
            f"the operators recorded for plan {path.plan_id!r} cannot be "
            "resolved as they were at decision time"
        ) from missing

    snapshot = record.context_fabric_snapshot
    execution = ProjectionEngine(
        reader=SnapshotReader(reader=reader, snapshot=snapshot), registry=operators
    ).execute(
        plan=plan,
        perspective=Perspective(
            principal_id=record.perspective_conditioning.principal_id,
            role=record.perspective_conditioning.role,
        ),
        tenant_id=snapshot.tenant_id,
        temporal_boundary=snapshot.temporal_boundary,
    )

    if execution.steps != path.steps:
        raise ReplayDivergence(
            "the re-executed step sequence differs from the recorded one "
            f"(recorded {[step.model_dump() for step in path.steps]}, "
            f"replayed {[step.model_dump() for step in execution.steps]}); a "
            "differing parameter hash means the operators are no longer the "
            "ones that ran"
        )

    reproduced_snapshot = snapshot_of_execution(
        execution=execution,
        tenant_id=snapshot.tenant_id,
        temporal_boundary=snapshot.temporal_boundary,
    )
    if reproduced_snapshot.graph_snapshot_id != snapshot.graph_snapshot_id:
        raise ReplayDivergence(
            "the re-executed graph substate does not match the recorded "
            f"snapshot {snapshot.graph_snapshot_id!r}; the state the decision "
            "was made against is not the state the graph now re-renders"
        )

    product = environment.rehydrate_product(
        record=record, projection=execution.projection
    )
    reproduced_address = content_hash(product)
    if reproduced_address != path.product_content_address:
        raise ReplayDivergence(
            f"the rehydrated product hashes to {reproduced_address!r}; the "
            f"record names {path.product_content_address!r}"
        )

    return ReplayOutcome(
        record=record,
        product=product,
        record_content_address=record_address,
        product_content_address=reproduced_address,
        graph_snapshot_id=reproduced_snapshot.graph_snapshot_id,
    )
