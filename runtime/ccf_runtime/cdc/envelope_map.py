"""Change event → :class:`SignalEnvelope` mapping (Pattern 1, FABR-09).

Whitepaper §8.3 Pattern 1 and DESIGN.md §2A.4.1: "change events map to
envelopes with ``observed_time`` from the transaction commit and ``source``
identifying the source *system*, not its location" (INV-CH8-01).

Pure, synchronous functions over typed inputs — the async part of the adapter
is I/O only (:mod:`ccf_runtime.cdc.adapter`), and keeping the mapping sync is
what makes it directly unit-testable and replayable.

Three properties this module exists to guarantee:

**Nothing is interpreted.** The row image travels into ``raw_payload``
unchanged, in the *source's* column vocabulary. The one field this module adds
is the change operation itself, written under a key the deployment names
(``change_op_key``) — the op is source vocabulary too, and naming its key here
would be the SDK holding a value (CINV-01). What that op then *means* for the
graph is L2's business: a ``u`` produces a claim whose content differs from its
predecessor and therefore supersedes it, and a ``d`` produces a terminal
tombstone claim that supersedes the last live one. Neither is ever a graph
DELETE — the graph is append-only-forward with logical supersession
(INV-CH7-04, INV-CH7-21).

**Identity is deterministic.** ``envelope_id`` is the content hash of the
event's source coordinates, commit timestamp, operation and image. The same
change event mapped twice yields the same id, so a re-delivered or replayed
stream collapses under the graph's idempotent upsert and under lineage
set-union (INV-CH7-17) instead of manufacturing history.

**Tenant scope is never taken from the payload.** ``tenant_id`` is a keyword
argument supplied by the adapter's deployment configuration. A source system
that could name its own tenant would be a cross-tenant spoofing surface
(T-04-20, INV-CH7-16).

Malformed events raise :class:`CDCMappingError` rather than being skipped: a
silently dropped change event is a graph that is quietly wrong, which is worse
than a stream that stops (T-04-21).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import ValidationError

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

__ccf_mode__ = "algorithmic"

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

#: The Debezium-style operation grammar this reference adapter reads. These are
#: tokens of the *wire format* the adapter parses, in the same sense that
#: ``{`` is a token of JSON — not domain values and not a routing table.
ChangeOperation = Literal["c", "u", "d"]


class CDCMappingError(ValueError):
    """A change event could not be normalized into a valid envelope.

    Raised — never swallowed — for an unparseable event, an unknown operation,
    an unknown field (``extra=forbid`` on the event contract), or an operation
    whose required row image is missing. The adapter surfaces it to the caller
    with the offending record's position, so a bad stream is diagnosable.
    """


class ChangeSource(CCFContract):
    """The change event's source coordinates.

    Attributes:
        connector: Logical name of the capture connector that emitted the
            event. One source *system* may be captured by several connectors,
            so this is part of the event's coordinates, not its identity — the
            system identity on the envelope comes from adapter configuration.
        db: Source database, in the source's own naming.
        table: Source table, in the source's own naming.

    These are coordinates, never a location: no host, no port, no connection
    string. L records source identity, not location (INV-CH8-01), and an
    envelope id derived from a hostname would not survive a migration.
    """

    connector: str
    db: str
    table: str


class ChangeEvent(CCFContract):
    """One Debezium-style change event, validated at the boundary.

    DESIGN.md §2A.4.1. ``extra=forbid`` is inherited from
    :class:`~ccf.contracts.base.CCFContract` and is doing real work here: this
    is the fabric's outermost trust boundary, and an unrecognized field means
    the adapter and the connector disagree about the wire format.

    Attributes:
        op: ``c`` create, ``u`` update, ``d`` delete.
        source: Source coordinates of the change.
        ts_ms: Transaction commit time, epoch milliseconds. Becomes the
            envelope's ``observed_time`` — the source's own statement of when
            the change happened, which is exactly what the T axis wants
            (INV-CH7-14).
        before: Row image prior to the change, when the connector emits one.
        after: Row image after the change.
    """

    op: ChangeOperation
    source: ChangeSource
    ts_ms: int
    before: Mapping[str, Any] | None = None
    after: Mapping[str, Any] | None = None


def parse_change_event(raw: object) -> ChangeEvent:
    """Validate one decoded change record into a :class:`ChangeEvent`.

    Args:
        raw: A decoded JSON object, as produced by the transport.

    Returns:
        The validated event.

    Raises:
        CDCMappingError: ``raw`` is not an object, carries an unknown field, an
            unknown operation, or a malformed value. Pydantic's report is
            preserved in the message — the operator debugging a broken
            connector needs to know *which* field.
    """
    if not isinstance(raw, Mapping):
        raise CDCMappingError(
            f"change event must be a JSON object, got {type(raw).__name__}"
        )
    try:
        return ChangeEvent.model_validate(dict(raw))
    except ValidationError as error:
        raise CDCMappingError(f"invalid change event: {error}") from error


def change_image(event: ChangeEvent) -> Mapping[str, Any]:
    """Return the row image that carries the event's asserted state.

    A create or an update asserts the ``after`` image; a delete asserts the
    ``before`` image, because the last thing the source could say about the row
    is what it looked like when it went away. A tombstone with no image is not
    a fact the fabric can record, so it is an error rather than an empty claim.

    Raises:
        CDCMappingError: the operation's required image is absent.
    """
    image = event.before if event.op == "d" else event.after
    if image is None:
        required = "before" if event.op == "d" else "after"
        raise CDCMappingError(
            f"change event with op {event.op!r} requires a {required!r} row "
            "image; the fabric refuses to record a change it cannot describe"
        )
    return image


def commit_time(event: ChangeEvent) -> datetime:
    """The transaction commit instant as an explicit UTC datetime.

    Epoch milliseconds are split into whole seconds plus a millisecond
    remainder rather than divided: float division would put a binary
    floating-point value on the T axis, and the canonical serializer rejects
    floats precisely because they are not bit-stable (D-IMPL-26).
    """
    seconds, milliseconds = divmod(event.ts_ms, 1000)
    return datetime.fromtimestamp(seconds, UTC) + timedelta(
        milliseconds=milliseconds
    )


def envelope_id_for(*, system_id: str, event: ChangeEvent) -> str:
    """Deterministic identity for one change event.

    The hash covers the source coordinates, the commit timestamp, the operation
    and the asserted image, so re-delivery of the same change is recognizably
    the same signal (idempotent upsert, lineage set-union) while two genuinely
    different changes at the same instant remain distinct.

    Raises:
        CDCMappingError: the event's required row image is absent.
    """
    return content_hash(
        {
            "system_id": system_id,
            "connector": event.source.connector,
            "db": event.source.db,
            "table": event.source.table,
            "op": event.op,
            "ts_ms": event.ts_ms,
            "image": {key: str(value) for key, value in change_image(event).items()},
        }
    )


def to_envelope(
    raw: object,
    *,
    tenant_id: str,
    system_id: str,
    change_op_key: str,
    ingestion_timestamp: datetime,
) -> SignalEnvelope:
    """Normalize one raw change record into a :class:`SignalEnvelope`.

    Args:
        raw: The decoded change record.
        tenant_id: Tenant scope, from adapter configuration. Keyword-only and
            never read from the event body (T-04-20).
        system_id: Logical identity of the source system (INV-CH8-01).
        change_op_key: Payload key the change operation is written under. The
            deployment names it, because it becomes part of the source
            vocabulary the entity-resolution spec is written against.
        ingestion_timestamp: When the fabric received the event.

    Returns:
        A validated envelope whose ``raw_payload`` is the row image plus the
        operation, and whose ``source_metadata`` carries the change coordinates
        for the operator who has to trace a claim back to a transaction.

    Raises:
        CDCMappingError: the record is malformed, or ``change_op_key`` collides
            with a column of the row image — silently shadowing a source column
            would corrupt the payload the graph is built from.
    """
    event = parse_change_event(raw)
    image = change_image(event)
    if change_op_key in image:
        raise CDCMappingError(
            f"change_op_key {change_op_key!r} collides with a column of the "
            f"row image from {event.source.table!r}; choose a key the source "
            "does not use rather than overwriting source data"
        )
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=envelope_id_for(system_id=system_id, event=event),
        source=SourceIdentity(system_id=system_id),
        ingestion_timestamp=ingestion_timestamp,
        observed_time=commit_time(event),
        raw_payload={**dict(image), change_op_key: event.op},
        source_metadata={
            "connector": event.source.connector,
            "db": event.source.db,
            "table": event.source.table,
            "op": event.op,
            "ts_ms": event.ts_ms,
        },
    )
