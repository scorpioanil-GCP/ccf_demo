"""The booted fabric's reader — every view carries the authority L2 enforces.

SEC-023 (``D-IMPL-374`` ruling (3) (a): classification authority enforced at
the construction of the consumer; the coordinator's ruling (1) of 2026-10-06).
SDK-defined mechanism beside the whitepaper's §7.3 read seam: whitepaper §7.3
(L2 is the only writer, so the authority a source holds is decided there) and
§7.4 (the Policy operator admits on a classification attribute). This is the
threading that carries the resolution spec's
:class:`~ccf.graph.protocols.ClassificationAuthority` from the composition
root (:func:`ccf.boot.boot`, the only place both the spec and the reader are in
hand) to every classification consumer: the views this reader returns carry
it, and the consumers — ``build_operator_registry``, ``PolicyFilter.apply`` and
this reader's own ``query`` — refuse without covering authority.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ccf.graph.protocols import (
    ClassificationAuthority,
    ClassificationAuthorityNotMinted,
    EntityRecord,
    GraphQuery,
    GraphReader,
    GraphView,
    RelationshipRecord,
    SnapshotPinnable,
    SourceAttestation,
    StoreSnapshotPin,
)

__ccf_mode__ = "algorithmic"

__all__ = ["governed_reader"]


class _ClassificationGovernedReader:
    """The booted fabric's reader: every view carries the authority L2 enforces.

    SEC-023 (``D-IMPL-374`` ruling (3) (a), coordinator ruling (1)). Wraps the
    store's reader so that :meth:`as_of` and :meth:`query` return views stamped
    with the :class:`~ccf.graph.protocols.ClassificationAuthority` of the
    resolution spec this fabric's :class:`~ccf.assembly.worker.AssemblyWorker`
    enforces — the stamp a classification consumer built into a registry or
    applied over the view checks (``require_classification_authority``) — and
    so that a :class:`~ccf.graph.protocols.GraphQuery` carrying a
    classification map is refused before it is answered unless that authority
    governs every attribute it names. The stamp is a private attribute: the
    views are the inner reader's records, byte for byte.

    Everything else — ``attestation``, ``snapshot_pin``, backend internals — is
    the inner reader's, forwarded unchanged, so a reader that does not
    implement :class:`~ccf.graph.protocols.SnapshotPinnable` still does not.
    """

    def __init__(self, inner: GraphReader, authority: ClassificationAuthority) -> None:
        if not authority.minted:
            # Fix round 1, I-1 (b): a reader wrapped with a hand-built authority
            # would stamp views every consumer refuses; refuse it here, early.
            raise ClassificationAuthorityNotMinted(consumer="governed_reader")
        self._inner = inner
        self._authority = authority

    def as_of(self, *, tenant_id: str, at: datetime) -> GraphView:
        return self._inner.as_of(tenant_id=tenant_id, at=at)._with_classification_authority(
            self._authority
        )

    def query(self, q: GraphQuery) -> GraphView:
        if q.classification_attribute_by_class is not None:
            # The consumer here is the query itself (path 1 of D-IMPL-372's
            # amendment): refused before the substrate is asked anything.
            self._authority.require(q.classification_attribute_by_class, consumer="GraphQuery")
            # Checked: hand the store the stamped question, which is what lets
            # a store reader refuse every classification query that did not
            # come through here (the fifth path).
            q = q._with_classification_authority(self._authority)
        return self._inner.query(q)._with_classification_authority(self._authority)

    @property
    def attestation(self) -> SourceAttestation:
        return self._inner.attestation

    def entity_history(
        self, *, tenant_id: str, entity_uri: str
    ) -> tuple[EntityRecord, ...]:
        return self._inner.entity_history(tenant_id=tenant_id, entity_uri=entity_uri)

    def relationship_history(
        self, *, tenant_id: str, relationship_key: str
    ) -> tuple[RelationshipRecord, ...]:
        return self._inner.relationship_history(
            tenant_id=tenant_id, relationship_key=relationship_key
        )

    def __getattr__(self, name: str) -> object:
        # Backend internals a test or an adapter-specific caller reaches for.
        # Protocol membership is decided statically (`isinstance` on a
        # runtime-checkable Protocol does not consult `__getattr__`), which is
        # why every Protocol member is spelled out above and the pinnable
        # pair lives on the subclass below.
        return getattr(self._inner, name)


class _PinnableClassificationGovernedReader(_ClassificationGovernedReader):
    """The governed reader over a substrate that can pin — SEC-023, ``D-IMPL-374``.

    A separate class rather than two optional methods, because
    :class:`~ccf.graph.protocols.SnapshotPinnable` is asked structurally: the
    wrapper is pinnable exactly when the reader it wraps is, so the replay
    record's store pin is what it was before the wrapper existed.
    """

    _inner: Any

    def snapshot_pin(self) -> StoreSnapshotPin:
        pin: StoreSnapshotPin = self._inner.snapshot_pin()
        return pin

    def query_pinned(self, q: GraphQuery, *, pin: StoreSnapshotPin) -> GraphView:
        if q.classification_attribute_by_class is not None:
            self._authority.require(q.classification_attribute_by_class, consumer="GraphQuery")
            q = q._with_classification_authority(self._authority)
        view: GraphView = self._inner.query_pinned(q, pin=pin)
        return view._with_classification_authority(self._authority)


def governed_reader(
    inner: GraphReader, authority: ClassificationAuthority
) -> GraphReader:
    """Wrap ``inner`` so every view it returns carries ``authority``.

    SEC-023 (``D-IMPL-374`` ruling (3) (a)). Called once, by
    :func:`ccf.boot.boot`, with the store's reader and the authority boot
    minted from the resolution spec the fabric's
    :class:`~ccf.assembly.worker.AssemblyWorker` enforces; an authority boot
    did not mint is refused (:class:`~ccf.graph.protocols.ClassificationAuthorityNotMinted`). The result is
    :class:`~ccf.graph.protocols.SnapshotPinnable` exactly when ``inner`` is.
    A ``GraphQuery`` (or a pinned query) carrying a classification map is
    refused with :class:`~ccf.graph.protocols.UngovernedClassificationAttribute`
    before the substrate is asked anything, unless ``authority`` governs every
    attribute it names.
    """
    if isinstance(inner, SnapshotPinnable):
        return _PinnableClassificationGovernedReader(inner, authority)
    return _ClassificationGovernedReader(inner, authority)
