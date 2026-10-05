"""`CDCSourceAdapter` — the v0 reference ingress for Pattern 1 (FABR-09).

Whitepaper §8.3 Pattern 1: CDC reads committed transactions off the source's
replication log, leaving the source itself untouched — neither its query path
nor its schema is coupled to the fabric. DESIGN.md §2A.4.1; D-IMPL-04(b)
(ingestion is async and lives in ``ccf-runtime`` while the fabric core stays
synchronous).

**What this adapter is not.** It is not a CDC transport. It holds no Kafka
consumer, no Debezium client, no replication-slot cursor, and the SDK takes no
dependency on any of them: the transport is deployment infrastructure
(DESIGN.md §2A.4.1). What the SDK owns is the normalization contract, so the
reference feed is the plainest possible one — a JSONL file, or any iterable of
JSON lines a deployment's own consumer produces. Binding a real transport means
feeding this adapter lines, or implementing
:class:`~ccf.signal.source.SignalSourceProtocol` directly; either way nothing
downstream changes.

**What this adapter cannot do.** It cannot write. There is no ``GraphWriter``
and no ``GraphReader`` on this object, because ``SignalSourceProtocol`` has no
place to put one (DESIGN.md §2A.2.2). Envelopes go to the caller, the caller
hands them to the L2 :class:`~ccf.assembly.worker.AssemblyWorker`, and that is
the only route into L3 (INV-CH7-10, INV-CH8-05, T-04-22).

**That route carries no temporal write guard of its own.** This adapter stamps
``ingestion_timestamp`` from its injected clock, so its envelopes cannot ride the
paved road's per-question boundary; the caller that hands them to the writer
composes :class:`~ccf.signal.envelope.IngressTemporalBound` at its composition
root and judges each envelope before ``ingest``, or an envelope stamped outside
the tenant's window reaches L3 unrefused. Ruled outside SEC-008 B1 (Dave,
2026-10-04, `D-IMPL-364`): on the low road the guard is the adopter's.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable, Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from ccf.signal.envelope import SignalEnvelope, SourceIdentity

from ccf_runtime.cdc.envelope_map import CDCMappingError, to_envelope

__ccf_mode__ = "algorithmic"

__all__ = ["CDCSourceAdapter"]


def _utc_now() -> datetime:
    """Wall-clock ingestion time, always tz-aware.

    The clock is an injected seam (see :class:`CDCSourceAdapter`) so replay and
    tests can drive ingestion time deterministically; this is the default a
    deployment gets when it has no reason to override.
    """
    return datetime.now(UTC)


class CDCSourceAdapter:
    """Async :class:`~ccf.signal.source.SignalSourceProtocol` over a change feed.

    Args:
        system_id: Logical identity of the source system these changes come
            from. Identity, never location (INV-CH8-01) — a hostname here would
            bind the fabric's lineage to a deployment topology.
        change_op_key: Payload key the change operation is written under. The
            deployment names it and declares it in its entity-resolution spec,
            which is what lets L2 tell a create from an update from a delete
            without the SDK holding either the key or its meaning.
        source_path: JSONL file to read, one change event per line. Mutually
            exclusive with ``lines``.
        lines: An in-memory or streamed sequence of JSON lines, for deployments
            whose transport is not a file. Mutually exclusive with
            ``source_path``.
        clock: Ingestion-time source. Injected so a replayed feed produces
            identical envelopes; defaults to the UTC wall clock.

    Raises:
        ValueError: neither or both of ``source_path`` and ``lines`` given.
            Guessing which feed was meant is exactly the silent default
            D-IMPL-38 forbids.

    Note:
        There is no ``tenant_id`` on the constructor: tenancy is an argument of
        :meth:`envelopes`, keyword-only, so one adapter over a shared source
        cannot leak an emission into the wrong tenant by positional accident
        (INV-CH7-16, T-04-20).
    """

    def __init__(
        self,
        *,
        system_id: str,
        change_op_key: str,
        source_path: Path | str | None = None,
        lines: Sequence[str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if (source_path is None) == (lines is None):
            raise ValueError(
                "CDCSourceAdapter takes exactly one feed: either source_path "
                "or lines"
            )
        self._system_id = system_id
        self._change_op_key = change_op_key
        self._source_path = Path(source_path) if source_path is not None else None
        self._lines = tuple(lines) if lines is not None else None
        self._clock = clock or _utc_now

    def source_identity(self) -> SourceIdentity:
        """The logical identity of the system this adapter reads."""
        return SourceIdentity(system_id=self._system_id)

    def _read_lines(self) -> tuple[str, ...]:
        """Read the file feed off the event loop's thread."""
        assert self._source_path is not None  # guarded by __init__
        with self._source_path.open(encoding="utf-8") as handle:
            return tuple(handle)

    async def _feed(self) -> Iterable[str]:
        """The adapter's raw lines, whichever feed was configured.

        File reads go through :func:`asyncio.to_thread` because blocking the
        event loop in an ingestion adapter is how one slow source stalls every
        other one.
        """
        if self._lines is not None:
            return self._lines
        return await asyncio.to_thread(self._read_lines)

    async def envelopes(self, *, tenant_id: str) -> AsyncIterator[SignalEnvelope]:
        """Yield one validated envelope per change event in the feed.

        Blank lines are skipped — they are framing, not data. Everything else
        that fails to normalize raises :class:`CDCMappingError` carrying the
        record's line number: a change event the fabric cannot represent stops
        the stream rather than leaving a hole in the graph nobody can see
        (T-04-21).

        Raises:
            CDCMappingError: a record is unparseable or malformed.
        """
        for number, line in enumerate(await self._feed(), start=1):
            text = line.strip()
            if not text:
                continue
            try:
                raw = json.loads(text)
            except json.JSONDecodeError as error:
                raise CDCMappingError(
                    f"line {number} of the change feed is not valid JSON: {error}"
                ) from error
            try:
                yield to_envelope(
                    raw,
                    tenant_id=tenant_id,
                    system_id=self._system_id,
                    change_op_key=self._change_op_key,
                    ingestion_timestamp=self._clock(),
                )
            except CDCMappingError as error:
                raise CDCMappingError(
                    f"line {number} of the change feed: {error}"
                ) from error
