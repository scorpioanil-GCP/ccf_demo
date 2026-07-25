"""Pattern 1 — the CDC→G reference ingress (whitepaper §8.3; DESIGN.md §2A.4.1).

A Debezium-*style* change stream is normalized into
:class:`~ccf.signal.envelope.SignalEnvelope` values and handed to L2. Nothing
here holds a graph handle: the adapter emits envelopes, the Assembly worker
writes, and that is the whole of the ingress contract (INV-CH8-05,
single-writer).

The package deliberately depends on no CDC transport. Kafka, Debezium Server,
Postgres logical replication and their queues are *deployment infrastructure*
(DESIGN.md §2A.4.1, "the specific CDC transport is deployment infrastructure,
not SDK mechanism"); what the SDK owns is the envelope shape the transport's
output has to arrive in. A file or an in-memory line stream is therefore the
reference feed, and a deployment that swaps in its own consumer changes
nothing else.

Runtime package, async per D-IMPL-04(b).
"""

from __future__ import annotations

from ccf_runtime.cdc.envelope_map import (
    CDCMappingError,
    ChangeEvent,
    ChangeSource,
    change_image,
    commit_time,
    envelope_id_for,
    parse_change_event,
    to_envelope,
)

__all__ = [
    "CDCMappingError",
    "ChangeEvent",
    "ChangeSource",
    "change_image",
    "commit_time",
    "envelope_id_for",
    "parse_change_event",
    "to_envelope",
]
