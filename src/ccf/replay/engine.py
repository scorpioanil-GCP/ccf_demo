"""The replay engine: a recorded decision, reproduced and hash-verified.

Whitepaper §7.10 (every decision forensically reconstructible years later
against the exact fabric state at decision time — INV-CH7-79/86); D-IMPL-06
(logical snapshots); D-IMPL-26 (exact-version artifact resolution); D-IMPL-44
(the re-hydration path); DESIGN.md §2B.5.

The pipeline, in order, with each step's failure mode named:

1. **Resolve the record** at its content address. A missing record is
   :class:`ReplayUnresolvable` — never the nearest one, never the newest under
   the name. The **raw fetched bytes** are re-hashed on arrival, before any
   model validation, so a substrate that returned the wrong artifact is caught
   here rather than believed (T-04-17, D-IMPL-89).

   That read path is :func:`resolve_artifact`, which is **parametrized by
   contract rather than fixed to the decision record**, plus
   :func:`resolve_artifact_at_uri` for the named form. A replay resolves
   whatever a record names, and the discipline — exact version, no fallback,
   re-hash on arrival, ``@latest`` refused — is identical for every class, so it
   is stated once. ``ccf.admission-record`` (D-IMPL-58 reading (d)) resolves
   through it as any other class does; no federation-shaped special case exists
   inside this engine, which is what keeps the seam described in one place
   rather than two.
2. **Resolve every Control Plane binding at its exact recorded version.** A
   control plane that has lost the version a decision was made under cannot say
   what that decision saw; that is :class:`ReplayUnresolvable`, not a fallback.
3. **Resolve the projection plan and operators** through the deployment's
   :class:`ReplayEnvironment`. The SDK cannot know a deployment's Π or its
   operator parameters — they are user code and user configuration — so this is
   a seam. It is a *verified* seam: what the environment supplies is checked
   against the record, never trusted.
4. **Re-execute** against a :class:`~ccf.replay.snapshots.SnapshotReader` pinned
   to the recorded tenant and boundary — under the recorded dimension-2
   ``survivor_cap`` (D-10), so a capped decision re-executes the way it ran —
   then check that the executed step sequence — operator keys, categories, and
   parameter hashes, in order — equals the recorded one, and that the
   re-executed query-pin sequence — one ``content_hash`` per issued
   ``GraphQuery``, in order — equals the recorded dimension-5
   ``graph_query_sequence`` (D-11). Drifted parameters and a drifted question
   sequence both surface as :class:`ReplayDivergence` here rather than as a
   quietly different answer. A record carrying the pre-seam
   :data:`~ccf.replay.record.NO_GRAPH_QUERIES` sentinel asserts it predates
   the query seam, and the pin comparison stands down — that is the
   compatibility promise, not a hole: the snapshot and product checks below
   still hold it to the same answer.
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

import hashlib
from typing import Protocol, TypeVar, runtime_checkable

from ccf.artifacts.protocol import (
    ArtifactStoreError,
    ArtifactStoreProtocol,
    MovingTargetRefused,
)
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol
from ccf.graph.protocols import GraphReader
from ccf.products.contract import ContextProductContract
from ccf.products.request import request_seeds
from ccf.projection.engine import OperatorRegistry, ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionOutput, ProjectionPlan
from ccf.replay.record import NO_GRAPH_QUERIES, DecisionReplayRecord
from ccf.replay.snapshots import SnapshotReader, snapshot_of_execution

__ccf_mode__ = "algorithmic"

__all__ = [
    "ReplayDivergence",
    "ReplayEnvironment",
    "ReplayError",
    "ReplayOutcome",
    "ReplayUnresolvable",
    "replay",
    "resolve_artifact",
    "resolve_artifact_at_uri",
]

#: Any contract a record can name. Bound to :class:`CCFContract` because the
#: resolution discipline needs exactly two things from an artifact — that it
#: parses closed-world, and that it has a canonical form to re-hash — and both
#: are properties of that base rather than of any particular class.
_ArtifactT = TypeVar("_ArtifactT", bound=CCFContract)


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

        **The debt in force comes off the record, and must not be re-measured**
        (15.5-11, D-IMPL-100). ``ContextProductContract.debt`` is inside the
        hashed body, so an implementation that omitted it — or recomputed it —
        returns a product the engine's address check rejects. It is
        reconstructible without a signature change because the record is
        already a parameter here: read
        ``record.content_generation_path.debt`` and carry it onto the rebuilt
        product verbatim. Re-deriving it is not an option even in principle:
        D_c is computed from observations and a ``now`` that neither the record
        nor the projection re-derives, so a fresh assessment would be a
        different decision wearing this one's identifier. A record carrying the
        ``None`` sentinel asserts its decision had no assessment, and the
        rebuilt product carries ``None`` in turn.

        **What the debt pointed at comes off the record too, and an
        implementation that omits it diverges** (15.6-06, D-IMPL-118).
        ``ContextProductContract.debt_evidence`` is a *top-level* vessel field
        rather than a member of the assessment, so it does not ride ``debt``
        back: read ``record.content_generation_path.debt_evidence`` and carry
        it onto the rebuilt product verbatim. It is reconstructible without a
        signature change for the same reason ``debt`` is — the record is
        already a parameter here — but only because dimension 5 was given a
        matching member; :class:`~ccf.projection.plan.ProjectionOutput` carries
        exactly ``(plan_id, payload)`` and names no evidence at all. A record
        carrying :data:`~ccf.halflife.assessment.NO_DEBT_EVIDENCE` asserts its
        decision pointed at nothing, and the rebuilt product asserts the same.

        **When the sources last published comes off the record too** (15.6-07,
        D-IMPL-117 gap 2). ``ContextProductContract.source_refresh_recency`` is
        the second top-level vessel field under the same D-IMPL-118 placement,
        so it does not ride ``debt`` back either: read
        ``record.content_generation_path.source_refresh_recency`` and carry it
        onto the rebuilt product verbatim. Re-deriving it is not an option even
        in principle — a refresh instant is a fact the deployment declared
        about a source at assembly time, and a rehydrator that asked the source
        again would be recording today's answer against a decision made against
        yesterday's. A record carrying
        :data:`~ccf.halflife.assessment.NO_SOURCE_REFRESH_RECENCY` asserts its
        decision recorded no refresh instants, and the rebuilt product asserts
        the same.

        **What the signal obliged comes off the record too — and re-resolving
        it is the failure this one guards** (15.6-08, D-IMPL-117 gap 3).
        ``ContextProductContract.obligation_in_force`` is the third top-level
        vessel field under the same D-IMPL-118 placement: read
        ``record.content_generation_path.obligation_in_force`` and carry it onto
        the rebuilt product verbatim. Unlike the two members above, an
        implementation *can* obtain a plausible value elsewhere — the
        deployment's current :class:`~ccf.controlplane.artifacts.DebtProfile`
        binds an obligation to the very same signal — and that is exactly what
        must not be done. A profile rebound since the decision would reproduce
        the obligation in force **now** against a decision made under the one in
        force **then**, which is the substitution CLAUDE.md §7.4 and D-IMPL-26
        forbid: replay resolves exact versions, never "latest". The engine's
        address check catches it, because the value is inside the hashed body.
        A record carrying
        :data:`~ccf.halflife.assessment.NO_OBLIGATION_IN_FORCE` asserts its
        decision was under no bound obligation, and the rebuilt product asserts
        the same.
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


def resolve_artifact(
    *,
    store: ArtifactStoreProtocol,
    content_address: str,
    contract: type[_ArtifactT],
) -> _ArtifactT:
    """Resolve one recorded artifact at its **exact** content address.

    The replay plane's single read path, stated once and parametrized by
    contract rather than duplicated per artifact class. Generality is the point:
    a replay resolves whatever a record names — a
    :class:`~ccf.replay.record.DecisionReplayRecord`, a
    ``ccf.admission-record`` (D-IMPL-58 reading (d)), a future class — and the
    resolution *discipline* is identical in every case, so a per-class resolver
    would be the same rule written down N times and a place for the (N+1)th to
    differ. Nothing about federation is special-cased inside the replay engine;
    an admission record resolves by class exactly as any other artifact does.

    Two guarantees, both structural rather than procedural:

    * **Exact version, never a fallback.** A miss is
      :class:`ReplayUnresolvable`. Substituting a nearby or newer artifact would
      produce a confident answer about a decision that never happened, which is
      worse than no answer (CLAUDE.md §7.4, D-IMPL-26).
    * **The raw fetched bytes are re-hashed on arrival, before validation**
      (D-IMPL-89). The put-time address *is* the sha256 of the stored canonical
      bytes, and the store's ``get`` contract promises those exact bytes back —
      so byte fidelity is the whole tamper claim, verified model-class-free. A
      substrate that returned the wrong artifact is *caught* rather than
      believed (T-04-17, T-06-102), and the "exact version" claim rests on
      arithmetic rather than on the store's good behaviour. The check is
      deliberately **not** a re-hash of the re-validated model: canonicalizing
      a rebuilt model serializes every sentinel-defaulted field a *later*
      contract version added, so an honest record written before a record
      extension would re-hash to a different address and trip the tamper check
      — the exact failure D-IMPL-89 rules out. Byte-first verification is what
      makes the sentinel-default extension strategy (D-IMPL-87 lineage) keep
      its compatibility promise.

    Args:
        store: Where the artifact lives (CLAUDE.md §7.4).
        content_address: The address to resolve. An address, not a name: names
            move, addresses do not.
        contract: The contract the bytes must satisfy. Supplied by the caller
            because deciding *which* contract a set of bytes is remains the
            caller's business — the store's contract is byte fidelity.

    Raises:
        ReplayUnresolvable: nothing is stored at that address.
        ReplayDivergence: the stored bytes do not hash to the address asked for.
    """
    try:
        payload = store.get(content_address=content_address)
    except (ArtifactStoreError, KeyError) as missing:
        raise ReplayUnresolvable(
            f"no {contract.__name__} is stored at {content_address!r}; "
            "replay resolves the exact recorded artifact and has no fallback "
            "(CLAUDE.md §7.4, D-IMPL-26)"
        ) from missing
    # Byte fidelity FIRST, validation second (D-IMPL-89): the address is the
    # sha256 of the stored canonical bytes, so the raw payload is the thing to
    # verify. Re-hashing a re-validated model here would serialize every
    # sentinel-defaulted field a later contract version added and reject
    # honest pre-extension records as tampered.
    reproduced = hashlib.sha256(payload).hexdigest()
    if reproduced != content_address:
        raise ReplayDivergence(
            f"the bytes at {content_address!r} hash to {reproduced!r}; the "
            f"store returned bytes that are not the {contract.__name__} that "
            "was asked for"
        )
    return contract.model_validate_json(payload)


def resolve_artifact_at_uri(
    *,
    store: ArtifactStoreProtocol,
    uri: str,
    contract: type[_ArtifactT],
) -> _ArtifactT:
    """Resolve a recorded artifact named by a D-IMPL-26 versioned URI.

    Naming resolution first, then :func:`resolve_artifact`. The two steps stay
    two calls for the reason :meth:`~ccf.artifacts.protocol.
    ArtifactStoreProtocol.resolve_uri` gives: identity is the content address
    and everything else is naming, and a combined call tempts an implementation
    to answer the naming question approximately.

    This is where ``@latest`` dies on the replay path. A URI is a string, and a
    string is where a moving target sneaks back in, so the refusal has to happen
    on the path a caller actually takes rather than only in a parser nobody is
    obliged to reach.

    Raises:
        ccf.artifacts.protocol.MovingTargetRefused: the URI asks for
            ``@latest``. Propagated unchanged, not translated: the caller did
            not fail to find something, the caller asked a question replay must
            never answer.
        ReplayUnresolvable: the URI is malformed, names no stored version, or
            names a version whose bytes are absent.
        ReplayDivergence: the resolved bytes do not hash to the address the name
            pointed at.
    """
    try:
        content_address = store.resolve_uri(uri=uri)
    except MovingTargetRefused:
        raise
    except (ArtifactStoreError, LookupError) as unresolvable:
        raise ReplayUnresolvable(
            f"{uri!r} names no stored {contract.__name__} version; replay "
            "resolves an exact version and has no fallback "
            "(CLAUDE.md §7.4, D-IMPL-26)"
        ) from unresolvable
    return resolve_artifact(
        store=store, content_address=content_address, contract=contract
    )


def _resolve_record(
    *, store: ArtifactStoreProtocol, record_address: str
) -> DecisionReplayRecord:
    """Resolve the decision record — the generic path, at a fixed contract."""
    return resolve_artifact(
        store=store,
        content_address=record_address,
        contract=DecisionReplayRecord,
    )


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
        reader=SnapshotReader(reader=reader, snapshot=snapshot),
        registry=operators,
        # The recorded dimension-2 cap, not the deployment's current one
        # (D-10): the pushed/in-process split depends on this value, so a
        # replay under a different cap would issue a different question
        # sequence — a re-computation wearing the decision's identifier.
        survivor_cap=record.policy_bindings.survivor_cap,
    ).execute(
        plan=plan,
        perspective=Perspective(
            principal_id=record.perspective_conditioning.principal_id,
            role=record.perspective_conditioning.role,
        ),
        tenant_id=snapshot.tenant_id,
        temporal_boundary=snapshot.temporal_boundary,
        # The recorded question's anchor, not the deployment's current one
        # (D-IMPL-111): the walk starting points are compiled into the query,
        # so a replay under different seeds would ask a different question
        # wearing the decision's identifier — the ``survivor_cap`` argument
        # one line up, applied to the other half of what shapes a query. A
        # record carrying no request yields ``None`` and replays exactly as
        # it did before the ruling.
        seeds=request_seeds(path.request),
    )

    if execution.steps != path.steps:
        raise ReplayDivergence(
            "the re-executed step sequence differs from the recorded one "
            f"(recorded {[step.model_dump() for step in path.steps]}, "
            f"replayed {[step.model_dump() for step in execution.steps]}); a "
            "differing parameter hash means the operators are no longer the "
            "ones that ran"
        )

    if path.graph_query_sequence != NO_GRAPH_QUERIES:
        # D-11: recompute the per-round-trip pins from the re-execution and
        # compare, in order. A record carrying the pre-seam sentinel asserts
        # it predates the query seam and is exempt — that is the sentinel's
        # compatibility promise (D-IMPL-89), and the snapshot and product
        # checks below still bind such a record to the same answer.
        replayed_pins = tuple(
            content_hash(query) for query in execution.executed_queries
        )
        if replayed_pins != path.graph_query_sequence:
            raise ReplayDivergence(
                "the re-executed query sequence differs from the recorded "
                f"pins (recorded {list(path.graph_query_sequence)!r}, "
                f"replayed {list(replayed_pins)!r}); the questions asked of "
                "the substrate are no longer the questions the decision "
                "asked (D-11, `GQ-20`)"
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
