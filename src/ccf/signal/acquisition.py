"""File-backed L1 acquisition — the reference implementation of the ingress seam.

Whitepaper §7.1 (Signal Layer) and §8.3 (integration patterns) supply the
layer this serves; the *acquisition boundary* framing is an SDK extension and
is marked as such rather than cited to the whitepaper (CLAUDE.md §11). The
ruling of record is `D-IMPL-282` (`R-09`, option 3a).

**The acquisition boundary is** :class:`~ccf.signal.source.SignalSourceProtocol`
**, and it already existed.** ``R-09`` was raised because the cp-05 product
hand-rolled its reads of an external store and recorded, in its own assembler,
that *"the SDK has no acquisition boundary for an external graph store — every
adapter in ``ccf.graph.backends`` is an L3 substrate the fabric OWNS"*
(`D-IMPL-277`).
That reading was about the **graph backends** and it is imprecise about L1:
every ingress mechanism the SDK has — CDC, MCP-source, semantic-layer import,
file and stream adapters — already reaches the fabric through one seam that
emits :class:`~ccf.signal.envelope.SignalEnvelope` and nothing else.
`D-IMPL-277` is therefore **resolved by discoverability**: what was missing was
not a Protocol but a file-backed reference implementation of the one that
exists, which `D-17` and CLAUDE.md §11 require and which this module supplies.
**No new Protocol is declared here, and none is needed.**

**How the acquisition parameters are carried, and why not as method
arguments.** An external acquisition is parameterized by the question being
asked — the product that motivated this row asks with a starting node, a walk
depth and two scope flags — while :meth:`SignalSourceProtocol.envelopes` takes
``tenant_id`` and nothing else. The bridge is the deployment-side adapter pattern
:class:`~ccf.signal.mcp_source.MCPSourceAdapter` already uses for its resource
selection: **the parameters are constructor state**. A deployment constructs
its source *for a question*, and the fabric then asks the constructed object
for its envelopes under the one parameter the Protocol carries. The narrowness
is a control rather than a limitation — a payload a previous read returned
cannot steer the next read, because there is no argument through which it
could (T-06-24, and the same reasoning as ``mcp_source``'s SSRF note).

Dave, ruling `R-09`, on what this abstraction is for:

    *"``SignalEnvelope.raw_payload`` is already the right acquisition vessel.
    The acquisition abstraction should answer how external source records
    enter CCF, not create a parallel normalization subsystem."*

So this module reads records and emits envelopes. It resolves no entity, mints
no relationship claim, and declares no second output type: interpretation is
L2's monopoly and L2 is the only writer to L3 (INV-CH7-10, CLAUDE.md §10). The
property is structural — :class:`SignalEnvelope` has no entity field and no
relationship field for an over-eager adapter to populate.

**Finding `24.10-F-04`, recorded rather than quietly repaired.** A Protocol
nobody could find is a different defect from a Protocol that does not exist,
and the two call for different fixes. `R-09` was scoped as the second and
measured as the first. `R-03` is the row that measures discoverability.

This module holds no source system name, no query, no predicate and no
threshold (CINV-01). Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ccf.contracts.canonical import content_hash
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

__ccf_mode__ = "algorithmic"

__all__ = ["AcquisitionRecordError", "FileRecordAcquisitionSource"]

#: Sentinel for "this record has no such key", so that a record whose member is
#: literally ``None`` is distinguishable from one that omits the member. Two
#: different facts, and ``dict.get``'s default would merge them.
_MISSING = object()


def _utc_now() -> datetime:
    """Wall-clock ingestion time, always tz-aware.

    The clock is an injected seam (see :class:`FileRecordAcquisitionSource`) so
    a replayed acquisition produces identical envelopes; this is the default a
    deployment gets when it has no reason to override.
    """
    return datetime.now(UTC)


class AcquisitionRecordError(ValueError):
    """A source document could not be read as records, naming what failed.

    Raised — never swallowed — for a document that cannot be read, is not
    valid JSON, is not a JSON array, or carries a member that is not an object
    (``raw_payload`` is a mapping, and a bare scalar or list is not a record
    the fabric can describe). The offending position is named, on the same
    reasoning as :class:`~ccf.signal.mcp_envelope_map.McpMappingError`: a
    silently dropped record is a graph that is quietly incomplete, which is
    worse than a stream that stops (T-06-25).
    """


class FileRecordAcquisitionSource:
    """A :class:`~ccf.signal.source.SignalSourceProtocol` over a file of records.

    The reference implementation CLAUDE.md §11 requires beside the ingress
    seam (`D-17`), and the offline half of the `R-09` evidence: records
    captured from a live external system replay through the same L1→L2 path
    with no estate reachable.

    Args:
        path: The document to read — a JSON array of record objects. A path is
            a *location*, which is why it is not the source's identity: see
            ``source`` below and INV-CH8-01.
        source: The logical identity of the system these records came from,
            declared by the deployment. The SDK never enumerates source
            systems, and a path here would bind the fabric's lineage to a
            filesystem that outlives nothing.
        selectors: The acquisition parameters, as exact-match constraints on
            top-level record members. Empty selects every record. **This is
            where a deployment's question lives** — see the module docstring on
            why the parameters are constructor state rather than arguments of
            :meth:`envelopes`. Which member means "anchor", "batch" or
            "family" is the deployment's to say; the SDK matches values and
            interprets none of them (CINV-01).
        clock: Ingestion-time source. Injected so a replayed acquisition
            produces identical envelopes; defaults to the UTC wall clock.

    Note:
        There is no ``tenant_id`` on the constructor: tenancy is an argument of
        :meth:`envelopes`, keyword-only, so one source over a shared document
        cannot leak an emission into the wrong tenant by positional accident
        (INV-CH7-16).
    """

    def __init__(
        self,
        *,
        path: Path,
        source: SourceIdentity,
        selectors: Mapping[str, Any] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._path = path
        self._source = source
        self._selectors = dict(selectors or {})
        self._clock = clock or _utc_now

    def source_identity(self) -> SourceIdentity:
        """The logical identity of the system these records came from."""
        return self._source

    def _records(self) -> Sequence[Mapping[str, Any]]:
        """Read the document and validate its shape, interpreting nothing.

        Raises:
            AcquisitionRecordError: the document is unreadable, is not valid
                JSON, is not an array, or carries a non-object member.
        """
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError as error:
            raise AcquisitionRecordError(
                f"the source document could not be read: {error}"
            ) from error
        try:
            document = json.loads(text)
        except json.JSONDecodeError as error:
            raise AcquisitionRecordError(
                f"the source document is not valid JSON: {error}"
            ) from error
        if not isinstance(document, list):
            raise AcquisitionRecordError(
                "the source document must be a JSON array of records; got "
                f"{type(document).__name__}"
            )
        for position, record in enumerate(document):
            if not isinstance(record, dict):
                raise AcquisitionRecordError(
                    f"record {position} is a {type(record).__name__}, which is "
                    "not a record the envelope's raw_payload can carry"
                )
        return document

    def _selected(self, record: Mapping[str, Any]) -> bool:
        """Whether ``record`` satisfies every constructor selector.

        Exact match on a top-level member. A record that does not carry a
        selector's key does **not** match: treating an absent key as a match
        would be the SDK guessing a default nobody declared (`D-IMPL-38`).
        """
        return all(record.get(key, _MISSING) == value
                   for key, value in self._selectors.items())

    def _envelope_id(self, record: Mapping[str, Any]) -> str:
        """Deterministic identity for one record.

        The hash covers the source system's identity and the record's content,
        so re-reading an unchanged document yields the same ids and collapses
        under the graph's idempotent upsert and lineage set-union
        (INV-CH7-17), while an edited record is recognizably new history. The
        record's *position* is deliberately excluded: a reordered document is
        the same set of facts.
        """
        return content_hash(
            {"system_id": self._source.system_id, "record": dict(record)}
        )

    async def envelopes(self, *, tenant_id: str) -> AsyncIterator[SignalEnvelope]:
        """Yield one validated envelope per selected record, for ``tenant_id``.

        The record lands in ``raw_payload`` verbatim — no key renamed, no class
        inferred, no identity minted from a payload value. ``observed_time`` is
        ``None`` and that is the answer rather than a gap: a file of records
        states no observed time, and deriving one from the read clock would be
        L1 interpreting.

        The record's position in the document is a fact about the *delivery*
        rather than about the fact, so it is quarantined into
        ``source_metadata``, exactly as
        :mod:`ccf.signal.mcp_envelope_map` quarantines the resource URI and
        media type.

        Selecting nothing yields an empty stream and is not an error: "no
        records matched" is an answer, and conflating it with "this source is
        broken" is the confusion the empty-operator guard exists downstream to
        catch.

        Args:
            tenant_id: Tenant scope for this drain. Keyword-only, per-call, and
                the only argument — the acquisition parameters are constructor
                state (see the module docstring).

        Raises:
            AcquisitionRecordError: the document is unreadable or malformed.
        """
        ingestion_timestamp = self._clock()
        for position, record in enumerate(self._records()):
            if not self._selected(record):
                continue
            yield SignalEnvelope(
                tenant_id=tenant_id,
                envelope_id=self._envelope_id(record),
                source=self._source,
                ingestion_timestamp=ingestion_timestamp,
                observed_time=None,
                raw_payload=dict(record),
                source_metadata={"record_index": position},
            )

