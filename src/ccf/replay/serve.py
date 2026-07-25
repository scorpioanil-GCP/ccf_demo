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

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from ccf.artifacts.protocol import ArtifactRef, ArtifactStoreProtocol
from ccf.contracts.base import CCFContract
from ccf.products.contract import ContextProductContract
from ccf.products.gates import ServableProduct
from ccf.replay.record import DecisionReplayRecord

__ccf_mode__ = "algorithmic"

__all__ = [
    "CapabilityForgeryError",
    "DeliveryCapability",
    "ReplayWriter",
    "ServedProduct",
    "serve",
]


class CapabilityForgeryError(TypeError):
    """A delivery capability was constructed outside a successful append."""


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
            store is never a second writer to the graph: this module imports
            nothing from :mod:`ccf.graph`.
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


def serve(
    *,
    product: ServableProduct,
    record: DecisionReplayRecord,
    replay_writer: ReplayWriter,
) -> ServedProduct:
    """Record the decision, then deliver the product — in that order, always.

    The whole function is one expression because there is nothing to sequence:
    the delivery is a method on the value the append returned.
    """
    return replay_writer.write_replay_record(record=record).deliver(product)
