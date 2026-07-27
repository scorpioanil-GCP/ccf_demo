"""MCP resource contents → :class:`SignalEnvelope` mapping (XPRC-01, L1).

SDK-defined (CLAUDE.md §7.1 — "MCP as ingress (L1)": MCP servers front-end
source data stores feeding the Signal Layer, and the SDK's MCP client
normalizes their outputs into the L1 event envelope). Whitepaper §8.3
Pattern 3 supplies the MCP integration edge this extends; the whitepaper
frames Pattern 3 as export only, so the ingress direction is CCF-SDK scope
and is marked as such here rather than cited to the whitepaper.

Pure, synchronous functions over typed inputs, split out of
:mod:`ccf.signal.mcp_source` exactly as :mod:`ccf_runtime.cdc.envelope_map`
is split out of its adapter: the async part of an ingress adapter is I/O, and
a mapping that never touches I/O is directly unit-testable and replayable.

Four properties this module exists to guarantee:

**Nothing is interpreted.** The resource's own content lands in
``raw_payload`` in the *source's* vocabulary. The MCP-shaped facts about the
delivery — the resource URI, its media type, the deployment's name for it,
and the server's ``_meta`` block — are quarantined into ``source_metadata``,
because they describe how the fact arrived rather than what it says. Neither
set bleeds into the other.

**``observed_time`` is ``None``, and that is the answer, not a gap.** MCP has
no observed-time concept: a resource read tells you what the server holds
now, never when the underlying event occurred. Deriving one — from the read
time, from a payload field the SDK guessed at, from the server's ``_meta`` —
would be L1 interpreting, which is L2's monopoly. ``None`` is the envelope's
documented way of saying "unknown", and L2 reconciles it against the
bitemporal T axis.

**Identity is deterministic.** ``envelope_id`` is the content hash of the
source coordinates plus the delivered content, so re-reading an unchanged
resource yields the same id and collapses under the graph's idempotent upsert
and lineage set-union (INV-CH7-17) instead of manufacturing history. A
polling ingress that minted a fresh id per read would grow the graph forever
without learning anything.

**Tenant scope is never taken from the payload.** ``tenant_id`` is a keyword
argument supplied by the adapter's deployment configuration. A remote MCP
server that could name its own tenant would be a cross-tenant spoofing
surface (T-06-26, INV-CH7-16).

Malformed content raises :class:`McpMappingError` naming which content item
failed, rather than being skipped: a silently dropped resource is a graph
that is quietly incomplete, which is worse than a stream that stops
(T-06-25).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from mcp.types import BlobResourceContents, TextResourceContents

from ccf.contracts.canonical import content_hash
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

__ccf_mode__ = "algorithmic"

__all__ = [
    "BLOB_PAYLOAD_KEY",
    "McpMappingError",
    "ResourceContents",
    "envelope_id_for",
    "payload_of",
    "source_metadata_of",
    "to_envelope",
]

#: The two content shapes an MCP ``read_resource`` can deliver. Named here so
#: the mapping's input type is one thing a caller can read, and so a third
#: shape appearing in a future MCP revision is a type error at this seam
#: rather than a silent fall-through.
ResourceContents = TextResourceContents | BlobResourceContents

#: The single key a binary resource's payload is written under. This is
#: envelope *framing* for a content shape that has no keys of its own — the
#: alternative is an envelope with no payload at all — and not a domain value
#: the SDK is choosing on a deployment's behalf (CINV-01).
BLOB_PAYLOAD_KEY = "blob"


class McpMappingError(ValueError):
    """One MCP content item could not be normalized into a valid envelope.

    Raised — never swallowed — for content that is not valid JSON, for JSON
    that is not an object (``raw_payload`` is a mapping, and a bare list or
    scalar is not a record the fabric can describe), and for an envelope that
    fails contract validation. The adapter re-raises it with the offending
    item's position, so a broken source is diagnosable.
    """


def payload_of(contents: ResourceContents) -> Mapping[str, Any]:
    """Return the opaque source payload carried by one content item.

    Text contents are parsed as JSON and must decode to an object; the keys
    that result are the *source's* vocabulary, never the fabric's, and nothing
    here inspects or renames them. Binary contents cannot have keys, so the
    base64 the server sent is carried verbatim under
    :data:`BLOB_PAYLOAD_KEY` — decoding it would be interpretation, and
    interpreting a blob is precisely what the Pattern 5 unstructured pipeline
    exists for, downstream of L1.

    Raises:
        McpMappingError: the text is not valid JSON, or decodes to something
            other than an object.
    """
    if isinstance(contents, BlobResourceContents):
        return {BLOB_PAYLOAD_KEY: contents.blob}
    try:
        decoded = json.loads(contents.text)
    except json.JSONDecodeError as error:
        raise McpMappingError(
            f"resource contents are not valid JSON: {error}"
        ) from error
    if not isinstance(decoded, dict):
        raise McpMappingError(
            "resource contents must decode to a JSON object; got "
            f"{type(decoded).__name__}, which is not a record the envelope's "
            "raw_payload can carry"
        )
    return decoded


def source_metadata_of(
    contents: ResourceContents, *, resource_name: str
) -> Mapping[str, Any]:
    """Return the MCP-shaped facts about how this content was delivered.

    Quarantined out of ``raw_payload`` on purpose: the URI, the media type,
    the deployment's own name for the resource, and the server's ``_meta``
    block all describe the *delivery*, not the fact. Mixing them into the
    payload would put fabric-side vocabulary into the source's namespace,
    where an entity-resolution spec written against the source could collide
    with it (the same collision :mod:`ccf_runtime.cdc.envelope_map` refuses
    for ``change_op_key``).

    ``_meta`` is spelled with its MCP wire name rather than the Python
    attribute name, because this block is a record of what the server said.
    """
    return {
        "uri": str(contents.uri),
        "mimeType": contents.mimeType,
        "resource_name": resource_name,
        "_meta": contents.meta,
    }


def envelope_id_for(
    *,
    system_id: str,
    resource_name: str,
    contents: ResourceContents,
) -> str:
    """Deterministic identity for one delivered content item.

    The hash covers the source system's identity, the deployment's name for
    the resource, the resource URI, and the delivered content itself. Two
    reads of an unchanged resource are therefore recognizably the same signal,
    while a changed resource — or the same content served at a different URI —
    is a different one.

    The server's ``_meta`` is deliberately *not* in the hash: it is
    server-side annotation that may vary per response, and letting it into
    identity would make an idempotent re-read look like new history.
    """
    return content_hash(
        {
            "system_id": system_id,
            "resource_name": resource_name,
            "uri": str(contents.uri),
            "mimeType": contents.mimeType or "",
            "content": (
                contents.blob
                if isinstance(contents, BlobResourceContents)
                else contents.text
            ),
        }
    )


def to_envelope(
    contents: ResourceContents,
    *,
    tenant_id: str,
    system_id: str,
    resource_name: str,
    ingestion_timestamp: datetime,
) -> SignalEnvelope:
    """Normalize one MCP content item into a :class:`SignalEnvelope`.

    Args:
        contents: One item of a ``read_resource`` result.
        tenant_id: Tenant scope, from adapter configuration. Keyword-only and
            never read from the delivered content (T-06-26).
        system_id: Logical identity of the source system this MCP server
            fronts. **Identity, never location** (INV-CH8-01) — the server's
            URL says where the deployment currently reaches the system, and
            putting it here would bind the fabric's lineage to a topology that
            outlives nothing.
        resource_name: The deployment's own name for the resource being read.
        ingestion_timestamp: When the fabric received the content, from the
            adapter's injected clock.

    Returns:
        A validated envelope with ``observed_time`` unset — see the module
        docstring: MCP states no observed time, and L1 does not invent one.

    Raises:
        McpMappingError: the content is malformed, or the resulting envelope
            fails contract validation.
    """
    try:
        return SignalEnvelope(
            tenant_id=tenant_id,
            envelope_id=envelope_id_for(
                system_id=system_id,
                resource_name=resource_name,
                contents=contents,
            ),
            source=SourceIdentity(system_id=system_id),
            ingestion_timestamp=ingestion_timestamp,
            observed_time=None,
            raw_payload=payload_of(contents),
            source_metadata=source_metadata_of(
                contents, resource_name=resource_name
            ),
        )
    except ValueError as error:
        if isinstance(error, McpMappingError):
            raise
        raise McpMappingError(
            f"MCP contents did not normalize into a valid envelope: {error}"
        ) from error
