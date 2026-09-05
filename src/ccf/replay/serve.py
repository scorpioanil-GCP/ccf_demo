"""Serving a product *is* appending its replay record, then delivering.

Whitepaper §7.10 (replay enforced at every Context Product boundary, never
bolted on — INV-CH7-79); CLAUDE.md §11; 04-RESEARCH.md Pattern 5.

The shape of this module is the invariant. Rather than

    write_replay_record(record)
    deliver(product)          # two statements, one of them skippable

the successful append *returns* the capability to deliver:

    ReplayWriter.write_replay_record(record) -> DeliveryCapability
    DeliveryCapability.deliver(product)      -> ServedProduct

A caller with no capability has nothing to deliver with, and the only way to
obtain one is an append that succeeded. Should the store fail, the exception
propagates out of the append and there is no branch — none, not even a
mistaken one — that reaches delivery. That closes the repudiation threat
(T-04-10) structurally instead of by review.

:class:`DeliveryCapability` takes a module-private token, exactly as
:class:`~ccf.products.gates.ServableProduct` does, so the capability cannot be
fabricated. The honest claim is DESIGN.md §9's: no unforced path exists, and
every forced path fails at construction.

Note what :meth:`DeliveryCapability.deliver` accepts: a ``ServableProduct``,
never a bare contract. The two structural gates therefore compose — a delivered
product has passed all three validation gates *and* has a replay record, and
neither guarantee is reachable without the other.

Where Context Debt travels on this seam
---------------------------------------
It travels **inside** :attr:`ServedProduct.product`, not beside it. The
:class:`~ccf.halflife.assessment.DebtAssessment` in force is a field of
:class:`~ccf.products.contract.ContextProductContract` under D-IMPL-100, so it
crosses this seam as part of the vessel's own bytes and needs nothing from
``serve()``.

That placement was ruled against the alternative of a third field on
:class:`ServedProduct`, and the reason is measured rather than aesthetic: all
three shipped delivery paths serialize ``servable.product`` and **none** of them
reads ``servable.replay_ref``, so debt hung beside the product would have
reached an in-process caller and no wire consumer at any door. See
:mod:`ccf.products.contract` for the per-door table.

**``serve()`` gains no branch for it.** The whole invariant of this module is
that the successful append *returns* the delivery capability and no branch
reaches delivery; debt travels with the capability's payload or with the record,
and it never becomes a condition. A ``serve()`` that inspected debt would be a
second place a delivery could be refused, and the first one — the append — would
stop being the only one.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from ccf.artifacts.protocol import ArtifactRef, ArtifactStoreProtocol
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.graph.protocols import GraphQuery
from ccf.products.contract import ContextProductContract
from ccf.products.gates import ServableProduct
from ccf.replay.record import DecisionReplayRecord

__ccf_mode__ = "algorithmic"

__all__ = [
    "CapabilityForgeryError",
    "DeliveryCapability",
    "QueryPinMismatch",
    "QueryPinWriter",
    "ReplayWriter",
    "ServedProduct",
    "record_refusal",
    "serve",
]


class CapabilityForgeryError(TypeError):
    """A delivery capability was constructed outside a successful append."""


class QueryPinMismatch(ValueError):
    """The record's pinned query sequence and the serve seam's queries disagree.

    Raised by :func:`serve` before anything is persisted: a record appended
    beside query bytes it does not pin — or pinning bytes nobody handed the
    seam — is a pin an auditor can never resolve (T-15.2-28), and refusing at
    the seam is what keeps that unrepresentable on the governed path.
    """


class ServedProduct(CCFContract):
    """What a caller receives: the product, and where its record landed.

    The reference travels with the product deliberately. A consumer holding a
    Context Product can name the decision record that authorizes it, which is
    what makes the audit trail usable from the consuming side rather than only
    from the fabric's.
    """

    product: ContextProductContract
    replay_ref: ArtifactRef


_DELIVERY_TOKEN = object()


class DeliveryCapability:
    """The right to deliver one product, granted by a completed replay append."""

    def __init__(self, replay_ref: ArtifactRef, token: object) -> None:
        if token is not _DELIVERY_TOKEN:
            raise CapabilityForgeryError(
                "DeliveryCapability is minted only by "
                "ReplayWriter.write_replay_record; delivery is unreachable "
                "without a completed replay append (whitepaper §7.10, "
                "CLAUDE.md §11)"
            )
        self._replay_ref = replay_ref

    @property
    def replay_ref(self) -> ArtifactRef:
        """Reference to the record whose append granted this capability."""
        return self._replay_ref

    def deliver(self, product: ServableProduct) -> ServedProduct:
        """Release ``product`` to the caller, paired with its replay reference."""
        return ServedProduct(product=product.product, replay_ref=self._replay_ref)


class ReplayWriter:
    """Appends replay records to the ArtifactStore and grants delivery.

    Args:
        store: The artifact substrate (CLAUDE.md §7.4). Any conforming
            implementation — file-backed here, MCP-backed in I.3 — and the
            store is never a second writer to the graph: this module holds no
            graph handle and imports no reader and no writer (its one
            :mod:`ccf.graph` import is the frozen :class:`GraphQuery` *value*
            contract the pin surface persists).
        artifact_class: Which artifact class replay records are filed under.
            Deployment vocabulary, so it is supplied rather than assumed.
    """

    def __init__(
        self, *, store: ArtifactStoreProtocol, artifact_class: str
    ) -> None:
        self._store = store
        self._artifact_class = artifact_class

    def write_replay_record(
        self, *, record: DecisionReplayRecord
    ) -> DeliveryCapability:
        """Append ``record``; return the capability its success grants.

        The record is named by its own snapshot id and addressed by its content
        hash, so two appends of the same decision converge on one artifact
        rather than accumulating near-duplicates.

        Raises:
            Exception: whatever the store raises. Deliberately not caught: a
                failure to record is a failure to serve, and translating it
                into a softer outcome here would be the exact hole this design
                exists to close.
        """
        ref = self._store.put(
            tenant_id=record.tenant_id,
            artifact_class=self._artifact_class,
            name=record.context_fabric_snapshot.graph_snapshot_id,
            artifact=record,
        )
        return DeliveryCapability(ref, _DELIVERY_TOKEN)


class QueryPinWriter:
    """Persists executed queries' canonical bytes, content-addressed (D-11).

    The :class:`ReplayWriter` precedent applied to the query pins of 15.2-08:
    the record carries the ordered ``content_hash`` tuple (dimension 5,
    ``graph_query_sequence``); this writer lands the **full canonical bytes**
    of each pinned :class:`~ccf.graph.protocols.GraphQuery` in the
    ArtifactStore, keyed by that hash — so an auditor holding a pin resolves
    the literal question from the store without re-running anything, and a
    replay that recomputes the sequence can quote what disagreed. Two
    executions issuing the same question converge on one artifact, because
    the store's addressing is content addressing.

    The store is reached at the serve seam, never from inside the projection
    engine: the engine stays free of persistence collaborators, exactly as it
    holds no replay writer.

    Args:
        store: The artifact substrate (CLAUDE.md §7.4) — ordinarily the same
            store the deployment's :class:`ReplayWriter` appends to.
        artifact_class: Which artifact class query bytes are filed under.
            Deployment vocabulary, supplied rather than assumed — this
            project's examples and tests use ``"ccf.graph-query"``.
    """

    def __init__(
        self, *, store: ArtifactStoreProtocol, artifact_class: str
    ) -> None:
        self._store = store
        self._artifact_class = artifact_class

    def write_query_bytes(
        self, *, tenant_id: str, queries: tuple[GraphQuery, ...]
    ) -> tuple[ArtifactRef, ...]:
        """Persist every query's canonical bytes; return the refs, in order.

        Each query is named by its own ``content_hash`` — the same value the
        record pins — and the store's derived content address equals that
        hash (both are ``sha256(canonical_bytes(...))``), so either the name
        lane or the address lane resolves a pin to its bytes.

        Raises:
            Exception: whatever the store raises, deliberately uncaught — the
                :meth:`ReplayWriter.write_replay_record` posture: a failure to
                persist a pinned question must fail the serve, because a
                record whose pins cannot be resolved is the T-15.2-28
                repudiation threat made durable.
        """
        return tuple(
            self._store.put(
                tenant_id=tenant_id,
                artifact_class=self._artifact_class,
                name=content_hash(query),
                artifact=query,
            )
            for query in queries
        )


def serve(
    *,
    product: ServableProduct,
    record: DecisionReplayRecord,
    replay_writer: ReplayWriter,
    query_pin_writer: QueryPinWriter | None = None,
    executed_queries: tuple[GraphQuery, ...] = (),
) -> ServedProduct:
    """Record the decision, then deliver the product — in that order, always.

    **A refusal is recorded by the same writer, through**
    :func:`record_refusal`, **and delivered as a shell by the resolver rather
    than as a product** (``24.6-07``, ``D-IMPL-253`` Q13). The ordering
    sentence above is the whole seam and it does not weaken for a governed
    "no": the append happens first there too, and a shell that left the
    resolver before its record was appended would be a decision with no audit.
    What differs is only that there is nothing to deliver — so that path calls
    the writer directly and never reaches
    :meth:`DeliveryCapability.deliver`, which is typed to a
    :class:`~ccf.products.gates.ServableProduct` a refusal does not have.

    **The 15.2-08 pin ordering** (D-11, T-15.2-28): when the seam is handed
    the executed queries, their canonical bytes are persisted **before** the
    replay-record append, so no moment exists at which an appended record
    pins bytes the store does not hold — a recorded pin never dangles. The
    consistency of the two is checked first: the record's
    ``graph_query_sequence`` must equal the ``content_hash`` tuple of the
    queries handed in, in order, or nothing is persisted at all.

    The two new parameters default to the pre-15.2-08 posture — no pin
    writer, no queries — so every existing call site is byte-for-byte
    unchanged. A deployment on the governed path passes
    ``execution.executed_queries`` and a :class:`QueryPinWriter` constructed
    beside its :class:`ReplayWriter`.

    Raises:
        QueryPinMismatch: the record's pinned sequence and the handed-in
            queries disagree, or queries were handed in with no writer to
            persist them, or a configured writer was given a record that pins
            queries nobody handed in. Raised before any store write.
    """
    derived_pins = tuple(content_hash(query) for query in executed_queries)
    pinned = record.content_generation_path.graph_query_sequence
    if executed_queries and query_pin_writer is None:
        raise QueryPinMismatch(
            f"{len(executed_queries)} executed quer(y/ies) were handed to the "
            "serve seam with no QueryPinWriter to persist them; a record "
            "appended without its query bytes is a pin an auditor cannot "
            "resolve (D-11, T-15.2-28)"
        )
    if query_pin_writer is not None and derived_pins != pinned:
        raise QueryPinMismatch(
            f"the record pins {list(pinned)!r} but the serve seam was handed "
            f"queries hashing to {list(derived_pins)!r}; the pinned sequence "
            "records what ran, so the two must agree element-for-element "
            "(D-11, `GQ-20`)"
        )
    if query_pin_writer is not None and executed_queries:
        # Bytes first, record second: the append below must never publish a
        # pin the store cannot already resolve (T-15.2-28).
        query_pin_writer.write_query_bytes(
            tenant_id=record.tenant_id, queries=executed_queries
        )
    return replay_writer.write_replay_record(record=record).deliver(product)


def record_refusal(
    *, record: DecisionReplayRecord, replay_writer: ReplayWriter
) -> ArtifactRef:
    """Append a refusal's decision record; return where it landed (24.6-07).

    **SDK-defined** (CLAUDE.md §11); the ruling of record is ``D-IMPL-253``
    Q13 (Dave: *"Refusal is itself a decision and deserves the same
    five-dimensional replay model. Do not create second-class replay."*) with
    ``D-IMPL-256``'s invariant: *"Every governed determination that crosses a
    CCF delivery boundary — fulfilled or refused, tool or resource, authorized
    or denied — must reach the replay writer before the response is
    released."*

    :func:`serve`'s half for a determination that produced no product. It is
    the **same** :class:`ReplayWriter`, over the same artifact store, appending
    the same :class:`~ccf.replay.record.DecisionReplayRecord` — which is the
    substance of *"do not create second-class replay"*: a second writer, or a
    second record shape, would be exactly that.

    **Why this returns an** :class:`~ccf.artifacts.protocol.ArtifactRef`
    **rather than a** :class:`DeliveryCapability`. The capability exists
    because a served product must be unreachable without a completed append,
    and it is typed to a :class:`~ccf.products.gates.ServableProduct` for that
    reason. A refusal has none, so there is nothing for a capability to
    authorize; what the caller needs is the **address**, because
    :attr:`~ccf.products.refusal.RefusalEnvelope.replay_reference` is where it
    goes. Minting a capability nobody could spend, in order to look
    symmetrical, would be ceremony — and the ordering property is preserved by
    the same mechanism either way: this function appends, and a store failure
    propagates out of it with no branch reaching a returned shell.

    Args:
        record: The five-dimension record of the refusal, built by
            :func:`~ccf.replay.record.build_replay_record` with the refusal as
            its outcome.
        replay_writer: The deployment's own writer — the same one its served
            path uses, over the same store.

    Returns:
        The reference the append produced. Its
        :attr:`~ccf.artifacts.protocol.ArtifactRef.uri` is what the returned
        shell carries; the **recorded** shell inside the record carries the
        sentinel, because a record cannot contain its own address.

    Raises:
        Exception: whatever the store raises, deliberately uncaught — the
            :meth:`ReplayWriter.write_replay_record` posture: a failure to
            record is a failure to respond, and a governed "no" released
            without its record is the repudiation this module exists to close.
    """
    return replay_writer.write_replay_record(record=record).replay_ref
