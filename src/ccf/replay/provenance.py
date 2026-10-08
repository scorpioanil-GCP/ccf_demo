"""Record provenance: whether the fabric's own record writer filed an address (`D-IMPL-378`, item 3).

SDK-defined (CLAUDE.md §7.4, §10, §11); whitepaper §7.10 (a Decision Replay
record is the evidence a decision is reconstructed from, so what counts as
one is a governance question, not a parsing one).

**The bytes at an address say nothing about who filed them.** A
:class:`~ccf.replay.record.DecisionReplayRecord` names its tenant and
principal in its own bytes, and anyone who can file an artifact can file
bytes shaped as a record that name any tenant and any principal — a tenant's
own principal included, on its client lane, with an ordinary
``ArtifactWrite``. Dave's ruling on those bytes (item 3, 2026-10-07): they
*"may remain ordinary client artifacts only if their untrusted origin is
explicit and consumers cannot accept them as governed evidence. Otherwise
refuse that path until provenance is enforced."* This module is the
enforcement.

**The rule** is the one
``ccf_runtime.authz.delivery_boundary.govern_dereference`` applies before any
of its holds: a record is accepted only where the store's own naming shows the
address filed by the fabric's record writer — under a class the store's
:class:`~ccf.artifacts.protocol.WriteKinds` declares under ``ReplayMint``, a
kind minted only at composition that no door can obtain — and under the
tenant the record names. The writer files under its capability's tenant and
refuses a record naming any other
(:class:`~ccf.replay.serve.ReplayTenantMismatch`), so every record it filed
passes, and bytes filed any other way do not. Content addressing makes the
rule exact rather than heuristic: identical bytes are one artifact, so a copy
of a genuine record filed again under another name is still the genuine
record and still passes.

**Two readings, neither one of the Protocol's four verbs.** Attribution needs
the store's ``write_kinds`` declaration and its ``names_at`` introspection.
Both shipped stores answer both, and the erasure-consulting store reads both
through to the store it decorates. A store that answers neither — or only one
— cannot say who filed an address, so a record read through it is refused by
name (:class:`UnattributableRecordStore`), never accepted on the bytes' word:
*don't know* is not *pass*.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from ccf.artifacts.protocol import ArtifactName, ArtifactNotFound, WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.erasure.store import ErasureConsultingStore

__ccf_mode__ = "algorithmic"

__all__ = [
    "RecordNotFiledByRecordWriter",
    "UnattributableRecordStore",
    "filed_by_record_writer",
    "require_filed_by_record_writer",
]


class UnattributableRecordStore(TypeError):
    """A record was read through a store that cannot say who filed an address (`D-IMPL-378`).

    Attribution reads the store's :class:`~ccf.artifacts.protocol.WriteKinds`
    declaration (``write_kinds``) and its naming introspection
    (``names_at``); through an
    :class:`~ccf.erasure.ErasureConsultingStore`, the store it decorates must
    answer ``names_at`` too. A store missing either cannot show that the
    fabric's record writer filed what it returns, so nothing read through it
    is accepted as a record. A ``TypeError``, as
    ``ccf_runtime.authz.delivery_boundary.UnattributableDeliveryBoundaryError``
    is: a wiring defect, raised where an operator sees it, never a
    determination about a caller.
    """


class RecordNotFiledByRecordWriter(ArtifactNotFound):
    """No filing by the fabric's record writer, under the record's tenant, is at the address (`D-IMPL-378`).

    The store holds bytes at the address that parse as a record, and its
    naming shows no filing of the address under a ``ReplayMint`` class of its
    :class:`~ccf.artifacts.protocol.WriteKinds` under the tenant the record
    names — a record-shaped artifact on a client lane, say. Those bytes are no
    Decision Replay record, so nothing that is one is stored there.

    **A subclass of** :class:`~ccf.artifacts.protocol.ArtifactNotFound`, on
    the precedent of :class:`~ccf.artifacts.protocol.MalformedContentAddress`:
    it is *true* — no record the writer filed is stored at the address — and
    every caller that already handles an absent record handles this one
    identically, while a caller that wants the mechanism can catch it by name.
    The replay engine answers it as it answers any missing record,
    :class:`~ccf.replay.engine.ReplayUnresolvable`, with this chained as the
    cause.
    """


def _attribution(
    store: object,
) -> tuple[WriteKinds, Callable[..., Iterable[ArtifactName]]]:
    """The store's declaration and naming reading, or a refusal by name."""
    declared = getattr(store, "write_kinds", None)
    names_at = getattr(store, "names_at", None)
    substrate = store
    while isinstance(substrate, ErasureConsultingStore):
        # The decorator answers `names_at` by delegating; the store it wraps
        # must actually answer it, or the delegation raises at the first read.
        substrate = substrate.inner
    if (
        not isinstance(declared, WriteKinds)
        or not callable(names_at)
        or not callable(getattr(substrate, "names_at", None))
    ):
        raise UnattributableRecordStore(
            f"a record was read through a {type(store).__name__} over"
            f" {type(substrate).__name__}, which cannot say who filed an address"
            " (it answers no names_at or declares no WriteKinds); a Decision"
            " Replay record is accepted only where the store shows the fabric's"
            " own record writer filed it, so it is refused rather than read"
            " (D-IMPL-378)"
        )
    return declared, names_at


def filed_by_record_writer(
    store: object, *, content_address: str, tenant_id: str
) -> bool:
    """Whether ``store`` shows ``content_address`` filed by the fabric's record writer under ``tenant_id``.

    The ONE provenance check (`D-IMPL-378`): some name the store holds for the
    address is under ``tenant_id``, in a class its
    :class:`~ccf.artifacts.protocol.WriteKinds` declares under ``ReplayMint``.
    Reads naming only, never the bytes.

    Args:
        store: The store the record was read through — a shipped store, the
            erasure-consulting composition of one, or any store answering
            ``write_kinds`` and ``names_at``.
        content_address: Where the record was read from.
        tenant_id: The tenant the record names, which is the tenant its
            writer filed it under.

    Raises:
        UnattributableRecordStore: ``store`` cannot answer the question.
    """
    declared, names_at = _attribution(store)
    return any(
        named.tenant_id == tenant_id
        and ReplayMint in declared.for_class(named.artifact_class)
        for named in names_at(content_address=content_address)
    )


def require_filed_by_record_writer(
    store: object, *, content_address: str, tenant_id: str
) -> None:
    """Return only if the fabric's record writer filed ``content_address`` under ``tenant_id``.

    The form every SDK reader that turns stored bytes into a
    :class:`~ccf.replay.record.DecisionReplayRecord` calls after parsing them
    and before accepting anything they say (`D-IMPL-378`).

    Raises:
        RecordNotFiledByRecordWriter: no such filing — the bytes are not a
            record the fabric wrote, whatever they say.
        UnattributableRecordStore: ``store`` cannot answer the question.
    """
    if not filed_by_record_writer(
        store, content_address=content_address, tenant_id=tenant_id
    ):
        raise RecordNotFiledByRecordWriter(
            f"the store shows no filing of {content_address!r} by the fabric's"
            f" record writer under tenant {tenant_id!r} (a class its WriteKinds"
            " declares under ReplayMint); bytes filed any other way — a"
            " record-shaped artifact on a client lane included — are not a"
            " Decision Replay record (D-IMPL-378)"
        )
