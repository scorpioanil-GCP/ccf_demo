# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Durable, addressable replay evidence for per-question graphs (`D-IMPL-383`).

SDK-defined extension (CLAUDE.md §7.4, §8.3, §11 "Decision Replay is enforced
at write time"); whitepaper §7.10.1 is unchanged by it. Dimension 1 of the
record stays a logical fingerprint (``D-IMPL-06``) — this module stores no copy
of anything. It answers the one question the record cannot: **given a
decision's record address, where is the graph that decision read?**

**Why an index and not a content-addressed link artifact** (the reviewer's
instruction 2, adopted by Dave, 2026-10-15 20:27): a link stored by its own
content address cannot be found from the decision's address. The index is keyed
by the decision's record address, so lookup is one file read, never a scan and
never "the last file in the folder".

**When evidence is complete** (instruction 3). The record, the graph and the
mapping are separate writes and nothing here makes them one transaction. The
order is: a *pending* marker is written before the question's graph is minted;
the governed call writes its record; the graph is closed; the mapping is
published durably (staged, flushed, ``fsync``-ed, renamed, directory
``fsync``-ed); and only then is the pending marker removed and the outcome
returned. An interruption anywhere in between leaves the pending marker, which
:meth:`ReplayEvidenceIndex.incomplete` lists and which lookup reports as
incomplete — never as a successful replay.

**What is NOT claimed.** The mapping is ``fsync``-ed; the decision record is
written by :class:`~ccf.artifacts.file_store.FileArtifactStore`, which stages
and renames but does not ``fsync``, so after an operating-system crash or power
loss a published mapping can name a record that did not survive. Lookup then
reports the decision unavailable, by name. Retained evidence consumes disk,
nothing here deletes it, and it must be backed up; retention duration and
purge automation are follow-on work (instruction 6).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime
from pathlib import Path, PurePath
from typing import Any, Final, Literal

from pydantic import JsonValue, model_validator

from ccf.artifacts.protocol import CONTENT_ADDRESS_PATTERN
from ccf.contracts.base import CCFContract
from ccf.replay.engine import ReplayDivergence, ReplayError

__ccf_mode__ = "algorithmic"

__all__ = [
    "EVIDENCE_SCHEMA_VERSION",
    "EvidenceEntry",
    "PendingEvidence",
    "ReplayEvidenceAltered",
    "ReplayEvidenceIndex",
    "ReplayEvidenceUnavailable",
    "file_sha256",
    "require_record_address",
]

#: The index document schema. Bumped only by a ruled change; a reader meeting
#: another version refuses rather than guessing what the fields mean.
EVIDENCE_SCHEMA_VERSION: Final[Literal[1]] = 1

_DECISIONS: Final[str] = "decisions"
_PENDING: Final[str] = "pending"
_SUFFIX: Final[str] = ".json"
_READ_CHUNK: Final[int] = 1 << 20


class ReplayEvidenceUnavailable(ReplayError):
    """The evidence a decision's replay needs is absent or incomplete.

    Raised for a missing mapping, a mapping never published because the
    decision was interrupted, a retained graph that is gone, or a record the
    store no longer holds. Never raised for evidence that EXISTS and fails an
    integrity check — that is :class:`ReplayEvidenceAltered`, a divergence
    (the reviewer's instruction 4: *"Do not collapse corruption into
    'missing'"*).

    Attributes:
        record_address: The decision that cannot be replayed.
        path: The missing evidence, relative to the evidence root, when one
            file is what is missing; ``None`` otherwise.
    """

    def __init__(self, *, record_address: str, detail: str, path: str | None = None) -> None:
        self.record_address = record_address
        self.path = path
        where = f" (missing: {path})" if path is not None else ""
        super().__init__(f"replay evidence for decision {record_address} is unavailable{where}: {detail}")


class ReplayEvidenceAltered(ReplayDivergence):
    """The retained graph exists but its bytes are not the bytes the decision closed.

    A :class:`~ccf.replay.engine.ReplayDivergence`, so a caller that already
    treats divergence as a finding treats this identically.

    Attributes:
        record_address: The decision whose evidence changed.
        path: The graph, relative to the evidence root.
        expected_sha256: What the mapping recorded when the graph was closed.
        found_sha256: What the file hashes to now.
    """

    def __init__(self, *, record_address: str, path: str, expected_sha256: str, found_sha256: str) -> None:
        self.record_address = record_address
        self.path = path
        self.expected_sha256 = expected_sha256
        self.found_sha256 = found_sha256
        super().__init__(
            f"the retained graph {path} for decision {record_address} hashes to"
            f" {found_sha256}, and the mapping recorded {expected_sha256} when the"
            " question closed it; the evidence was altered after the decision"
        )


def require_record_address(record_address: str) -> str:
    """Return ``record_address`` if it is a content address; otherwise refuse.

    Checked before any path is built from it, so a lookup can never reach the
    filesystem through ``..``, an absolute path, or any other non-address.

    Raises:
        ValueError: it is not a content address.
    """
    if not CONTENT_ADDRESS_PATTERN.match(record_address):
        raise ValueError(f"{record_address!r} is not a content address (sha256, 64 lowercase hex)")
    return record_address


def _require_graph_name(graph: str) -> str:
    """A retained graph is named by a bare file name relative to the evidence root."""
    pure = PurePath(graph)
    if pure.is_absolute() or len(pure.parts) != 1 or graph in {".", ".."} or graph != pure.name:
        raise ValueError(f"{graph!r} is not a bare graph file name relative to the evidence root")
    return graph


def file_sha256(path: Path) -> str:
    """The sha256 of the file at ``path``, read in chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_READ_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


class PendingEvidence(CCFContract):
    """The explicit incomplete state: a question began and its mapping is not yet published.

    Written before the question's graph is minted, removed only after the
    mapping is durable. One that survives a restart is an interrupted
    decision.
    """

    schema_version: Literal[1]
    tenant_id: str
    graph: str
    product_class: str
    product_version: str
    subject: str
    parameters: dict[str, JsonValue]
    asked_at: datetime
    started_at: datetime


class EvidenceEntry(CCFContract):
    """One decision's published evidence mapping — the index document.

    Carries what the front-end's listing needs (when, about what, served or
    refused, and why) and where the decision's graph is. Everything here is
    already on the decision record or its request; the entry restates it so a
    listing needs no record reads, and the record stays the authority.

    Attributes:
        record_address: The decision record's content address — the index key.
        outcome: ``served`` or ``refused``.
        refusal_reason: The refusal envelope's reason; ``None`` when served.
        decided_at: The wall-clock instant the decision completed — never the
            deployment's clock, which a decision may read and must not be moved by.
        graph: The retained graph, relative to the evidence root; ``None`` for
            a refusal reached before any graph was minted.
        graph_required: Whether replay needs a graph. ``False`` states
            explicitly that none was required (instruction 5).
        graph_sha256: The graph's bytes when the question closed it.
    """

    schema_version: Literal[1]
    record_address: str
    tenant_id: str
    outcome: Literal["served", "refused"]
    refusal_reason: str | None
    product_class: str
    product_version: str
    subject: str
    parameters: dict[str, JsonValue]
    asked_at: datetime
    decided_at: datetime
    graph: str | None
    graph_required: bool
    graph_sha256: str | None

    @model_validator(mode="after")
    def _consistent(self) -> EvidenceEntry:
        require_record_address(self.record_address)
        if self.graph_required != (self.graph is not None):
            raise ValueError("graph_required must be true exactly when a graph is named")
        if (self.graph is None) != (self.graph_sha256 is None):
            raise ValueError("a named graph carries its sha256, and only a named graph does")
        if self.graph is not None:
            _require_graph_name(self.graph)
        if self.outcome == "served" and self.graph is None:
            raise ValueError("a served decision read a graph; its mapping must name it")
        if (self.outcome == "refused") != (self.refusal_reason is not None):
            raise ValueError("a refusal carries its reason, and only a refusal does")
        return self

    def involves(self, identifier: str) -> bool:
        """Whether ``identifier`` is this decision's subject or one of its parameter values."""
        if self.subject == identifier:
            return True
        for value in self.parameters.values():
            values = value if isinstance(value, list) else [value]
            if any(not isinstance(item, (dict, list)) and str(item) == identifier for item in values):
                return True
        return False


def _durable_write(target: Path, payload: bytes) -> None:
    """Stage, flush, fsync, rename, then fsync the directory."""
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        with staged.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, target)
    finally:
        staged.unlink(missing_ok=True)
    directory = os.open(target.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


class ReplayEvidenceIndex:
    """The decision → retained-graph mapping for one evidence root and one tenant.

    The evidence root is the deployment's ``scratch``: the per-question graphs
    are minted there and the default replay store lives there, so a scratch on
    a persistent filesystem is all the persistence this needs. The index lives
    beside them, under ``index_root``. A temporary scratch keeps today's
    ephemeral behavior; the index goes with it.
    """

    def __init__(self, *, evidence_root: Path, index_root: Path, tenant_id: str) -> None:
        self.evidence_root = evidence_root
        self.index_root = index_root
        self.tenant_id = tenant_id

    # --- writes ------------------------------------------------------------------------

    def begin(self, *, graph: str, request: Any, started_at: datetime) -> None:
        """Write the pending marker for a question about to mint ``graph``."""
        _require_graph_name(graph)
        marker = PendingEvidence(
            schema_version=EVIDENCE_SCHEMA_VERSION,
            tenant_id=self.tenant_id,
            graph=graph,
            product_class=request.schema_name,
            product_version=request.schema_version,
            subject=request.subject,
            parameters=request.model_dump(mode="json")["parameters"],
            asked_at=request.asked_at,
            started_at=started_at,
        )
        _durable_write(self._pending_path(graph), marker.model_dump_json().encode("utf-8"))

    def publish(self, entry: EvidenceEntry) -> None:
        """Publish ``entry`` durably, then clear its question's pending marker."""
        if entry.tenant_id != self.tenant_id:
            raise ValueError(f"this index is scoped to tenant {self.tenant_id!r}, not {entry.tenant_id!r}")
        _durable_write(self._decision_path(entry.record_address), entry.model_dump_json().encode("utf-8"))
        if entry.graph is not None:
            self._pending_path(entry.graph).unlink(missing_ok=True)

    # --- reads -------------------------------------------------------------------------

    def entry(self, record_address: str) -> EvidenceEntry | None:
        """This tenant's published mapping for ``record_address``, or ``None`` when it has none."""
        path = self._decision_path(require_record_address(record_address))
        try:
            payload = path.read_bytes()
        except FileNotFoundError:
            return None
        entry = EvidenceEntry.model_validate_json(payload)
        if entry.tenant_id != self.tenant_id:
            # Instruction 2: scoped to the instance AND the tenant. Another
            # tenant's mapping is not this tenant's evidence, and its existence
            # is not disclosed.
            return None
        if entry.record_address != record_address:
            raise ReplayDivergence(
                f"the evidence mapping filed under {record_address} names decision"
                f" {entry.record_address}; the index was altered"
            )
        return entry

    def graph_path(self, entry: EvidenceEntry) -> Path:
        """Where ``entry``'s graph is, under the evidence root."""
        if entry.graph is None:
            raise ValueError(f"decision {entry.record_address} retained no graph")
        return self.evidence_root / _require_graph_name(entry.graph)

    def decisions(
        self,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        involving: str | None = None,
    ) -> list[EvidenceEntry]:
        """This tenant's published decisions, in decision order.

        ``since`` and ``until`` bound ``decided_at`` inclusively; ``involving``
        keeps decisions whose subject or a parameter value equals it (a
        company, a facility). Incomplete decisions are not listed here; see
        :meth:`incomplete`.
        """
        found: list[EvidenceEntry] = []
        directory = self.index_root / _DECISIONS
        if not directory.is_dir():
            return found
        for path in directory.glob(f"*{_SUFFIX}"):
            entry = EvidenceEntry.model_validate_json(path.read_bytes())
            if entry.tenant_id != self.tenant_id:
                continue
            if since is not None and entry.decided_at < since:
                continue
            if until is not None and entry.decided_at > until:
                continue
            if involving is not None and not entry.involves(involving):
                continue
            found.append(entry)
        return sorted(found, key=lambda entry: (entry.decided_at, entry.record_address))

    def incomplete(self) -> list[PendingEvidence]:
        """Questions that began and never published a mapping — interrupted decisions."""
        directory = self.index_root / _PENDING
        if not directory.is_dir():
            return []
        published = {entry.graph for entry in self.decisions() if entry.graph is not None}
        markers = [PendingEvidence.model_validate_json(path.read_bytes()) for path in directory.glob(f"*{_SUFFIX}")]
        return sorted(
            (marker for marker in markers if marker.tenant_id == self.tenant_id and marker.graph not in published),
            key=lambda marker: (marker.started_at, marker.graph),
        )

    # --- layout ------------------------------------------------------------------------

    def _decision_path(self, record_address: str) -> Path:
        return self.index_root / _DECISIONS / f"{require_record_address(record_address)}{_SUFFIX}"

    def _pending_path(self, graph: str) -> Path:
        return self.index_root / _PENDING / f"{_require_graph_name(graph)}{_SUFFIX}"


class NoGraphRetained:
    """Stands in for the reader and environment of a refusal that minted no graph.

    The engine's pre-projection refusal path consults neither
    (:func:`~ccf.replay.engine.replay_refusal`), so this is never touched when
    the record and its mapping agree. If it IS touched, the record claims a
    graph read its mapping says never happened, and that is reported rather
    than answered from nothing.
    """

    def __init__(self, record_address: str) -> None:
        self._record_address = record_address

    def __getattr__(self, name: str) -> Any:
        # Instruction 4: the record and its mapping disagreeing is corruption,
        # never "missing".
        raise ReplayDivergence(
            f"replay of {self._record_address} asked the graph for {name!r}, and"
            " this decision's mapping states no graph was required; the record"
            " and its mapping disagree"
        )
