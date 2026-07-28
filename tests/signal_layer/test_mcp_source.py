"""The L1 MCP client ingress, field by field (XPRC-01; CLAUDE.md §7.1).

What this suite holds ``ccf.signal.mcp_source`` and
``ccf.signal.mcp_envelope_map`` to, each assertion drafted from what would
fail:

=========================================  ===================================
Invariant / requirement                    What would fail here
=========================================  ===================================
seam conformance (DESIGN.md §2A.2.2)       the adapter would stop satisfying
                                           ``SignalSourceProtocol`` and the
                                           composition root's wiring check
                                           would pass on a different shape
L1 does not interpret (INV-CH7-14)         an ``observed_time`` guessed from
                                           the read time or a payload field
                                           would appear on the envelope
payload/metadata separation                an MCP-shaped fact would land in
                                           ``raw_payload`` in the source's
                                           namespace, where a resolution spec
                                           could collide with it
identity, not location (INV-CH8-01)        the server address would reach
                                           ``source.system_id`` and pin the
                                           fabric's lineage to a topology
no silent drops (T-06-25)                  a malformed content item would be
                                           skipped, leaving a hole in the
                                           graph nobody can see
tenant isolation (T-06-26, D-23)           tenancy would be constructor state,
                                           and one adapter over a shared
                                           source would leak across principals
one shared client (D-IMPL-13)              the adapter would open a session of
                                           its own rather than going through
                                           ``ccf.mcp.client``
=========================================  ===================================

The transport is stubbed here so that these assertions are about the mapping
and the seam. The live proof against a real server in another OS process is
``tests/crossproc/test_mcp_ingress.py``.

Every domain value comes from ``tests/fixtures/banking/``. Delete the fixtures
and this file has nothing to assert (§6.4 applied to test code).
"""

from __future__ import annotations

import asyncio
import base64
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml
from mcp.types import (
    BlobResourceContents,
    ReadResourceResult,
    TextResourceContents,
)

import ccf.signal.mcp_source as mcp_source
from ccf.mcp.client import McpResourceClient
from ccf.signal.envelope import SignalEnvelope
from ccf.signal.mcp_envelope_map import (
    BLOB_PAYLOAD_KEY,
    McpMappingError,
    to_envelope,
)
from ccf.signal.mcp_source import MCPSourceAdapter
from ccf.signal.source import SignalSourceProtocol

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"

#: Never dialled: every test replaces the shared library's session runner, so
#: no transport code sees this. Named so it cannot be mistaken for an address.
UNUSED_URL = "unused://never-dialled"

#: A fixed ingestion instant. Injected, because an envelope whose timestamp
#: came from a wall clock does not replay.
INSTANT = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)


def _load(name: str) -> Any:
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source() -> Any:
    return _load("mcp_source.yaml")


@pytest.fixture(scope="module")
def events() -> Any:
    return _load("events.yaml")


def _uri(source: Any, name: str) -> str:
    """The resource URI the fixture server publishes ``name`` under."""
    return (
        f"{source['resource_uri_scheme']}://"
        f"{source['resource_uri_authority']}/{name}"
    )


def _text(source: Any, name: str, payload: Any) -> TextResourceContents:
    return TextResourceContents(
        uri=_uri(source, name),
        mimeType=source["mime_type"],
        text=json.dumps(payload),
    )


def _resources(source: Any, events: Any) -> dict[str, str]:
    """The deployment's resource selection: one resource per fixture event."""
    return {
        item["envelope_id"]: _uri(source, item["envelope_id"])
        for item in events["envelopes"]
    }


def _stub_reads(
    monkeypatch: pytest.MonkeyPatch, responses: dict[str, ReadResourceResult]
) -> list[str]:
    """Answer reads from ``responses``; record the URLs the adapter dialled.

    Patched at :func:`ccf.mcp.client.run_with_session` rather than on the
    adapter, so the stub only engages if the adapter really does route through
    the one shared client library (D-IMPL-13). An adapter that opened its own
    session would sail past this and fail on a connection error.
    """
    dialled: list[str] = []

    async def fake_run_with_session(*, url: str, operation: Any) -> Any:
        dialled.append(url)

        class _Session:
            async def read_resource(self, uri: Any) -> ReadResourceResult:
                return responses[str(uri)]

        return await operation(_Session())

    monkeypatch.setattr(mcp_source, "run_with_session", fake_run_with_session)
    return dialled


def _adapter(source: Any, resources: dict[str, str]) -> MCPSourceAdapter:
    return MCPSourceAdapter(
        system_id=source["system_id"],
        client=McpResourceClient(url=UNUSED_URL),
        resources=resources,
        clock=lambda: INSTANT,
    )


def _drain(
    adapter: MCPSourceAdapter, *, tenant_id: str
) -> tuple[SignalEnvelope, ...]:
    """Run the adapter's async emission to completion.

    ``asyncio.run`` per drain, mirroring the CDC slice: the async surface is
    ingestion's, not the fabric core's (D-IMPL-04(b)).
    """

    async def collect() -> tuple[SignalEnvelope, ...]:
        return tuple([e async for e in adapter.envelopes(tenant_id=tenant_id)])

    return asyncio.run(collect())


# --- the seam --------------------------------------------------------------


def test_the_adapter_satisfies_the_one_ingress_seam(source: Any) -> None:
    """Runtime conformance, which is what the composition root checks."""
    adapter = _adapter(source, {"r": _uri(source, "r")})
    assert isinstance(adapter, SignalSourceProtocol)
    assert adapter.source_identity().system_id == source["system_id"]


def test_the_adapter_refuses_an_empty_resource_selection(source: Any) -> None:
    """An ingress that would read nothing is a wiring mistake, not a default."""
    with pytest.raises(ValueError, match="at least one resource"):
        MCPSourceAdapter(
            system_id=source["system_id"],
            client=McpResourceClient(url=UNUSED_URL),
            resources={},
        )


def test_the_read_goes_through_the_shared_client_at_its_own_url(
    source: Any, events: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One resource, one shared-library call, at the injected client's URL.

    The URL assertion is the SSRF control's positive half: the address dialled
    is the one the composition root built into the client, and there is no
    argument through which anything else could have supplied one (T-06-24).
    """
    item = events["envelopes"][0]
    resources = {item["envelope_id"]: _uri(source, item["envelope_id"])}
    dialled = _stub_reads(
        monkeypatch,
        {
            resources[item["envelope_id"]]: ReadResourceResult(
                contents=[_text(source, item["envelope_id"], item["payload"])]
            )
        },
    )

    _drain(_adapter(source, resources), tenant_id=source["tenants"]["primary"])

    assert dialled == [UNUSED_URL]


# --- the mapping, field by field -------------------------------------------


def test_every_envelope_field_matches_the_mapping(
    source: Any, events: Any
) -> None:
    """Research Pattern 2's table, asserted row by row on one content item."""
    item = events["envelopes"][0]
    name = item["envelope_id"]
    contents = _text(source, name, item["payload"])

    envelope = to_envelope(
        contents,
        tenant_id=source["tenants"]["primary"],
        system_id=source["system_id"],
        resource_name=name,
        ingestion_timestamp=INSTANT,
    )

    assert envelope.tenant_id == source["tenants"]["primary"]
    assert envelope.source.system_id == source["system_id"]
    assert envelope.ingestion_timestamp == INSTANT
    # The row that is easiest to get wrong: MCP states no observed time, so
    # L1 states none either. A value here would be L1 interpreting.
    assert envelope.observed_time is None
    assert dict(envelope.raw_payload) == item["payload"]
    assert dict(envelope.source_metadata) == {
        "uri": _uri(source, name),
        "mimeType": source["mime_type"],
        "resource_name": name,
        "_meta": None,
    }


def test_the_system_id_is_the_declared_identity_not_any_part_of_the_address(
    source: Any, events: Any
) -> None:
    """INV-CH8-01, asserted against the address rather than for a constant.

    Comparing to the fixture's ``system_id`` alone would pass on an
    implementation that also leaked the address somewhere; this checks that
    the resource URI, and the scheme that makes it an address at all, are
    absent from the identity. The URI *authority* is deliberately not checked
    as a fragment: the fixture's organisation name legitimately appears in
    both, and a substring test there would assert a naming taboo rather than
    INV-CH8-01.
    """
    item = events["envelopes"][0]
    name = item["envelope_id"]

    envelope = to_envelope(
        _text(source, name, item["payload"]),
        tenant_id=source["tenants"]["primary"],
        system_id=source["system_id"],
        resource_name=name,
        ingestion_timestamp=INSTANT,
    )

    assert envelope.source.system_id == source["system_id"]
    for fragment in (
        f"{source['resource_uri_scheme']}://",
        _uri(source, name),
        "://",
    ):
        assert fragment not in envelope.source.system_id
    # The URI is on the envelope — but in source_metadata, where it is a fact
    # about delivery, not in the identity the lineage is written against.
    assert envelope.source_metadata["uri"] == _uri(source, name)


def test_neither_namespace_bleeds_into_the_other(
    source: Any, events: Any
) -> None:
    """MCP-shaped facts stay out of the payload, and vice versa."""
    item = events["envelopes"][0]
    name = item["envelope_id"]

    envelope = to_envelope(
        _text(source, name, item["payload"]),
        tenant_id=source["tenants"]["primary"],
        system_id=source["system_id"],
        resource_name=name,
        ingestion_timestamp=INSTANT,
    )

    for mcp_key in ("uri", "mimeType", "resource_name", "_meta"):
        assert mcp_key not in envelope.raw_payload
    for payload_key in item["payload"]:
        assert payload_key not in envelope.source_metadata


def test_a_binary_resource_lands_as_opaque_base64(source: Any) -> None:
    """A blob is carried, never decoded — decoding is Pattern 5's, downstream."""
    encoded = base64.b64encode(b"\x00\x01scanned-agreement").decode("ascii")
    contents = BlobResourceContents(
        uri=_uri(source, "scan"),
        mimeType="application/pdf",
        blob=encoded,
    )

    envelope = to_envelope(
        contents,
        tenant_id=source["tenants"]["primary"],
        system_id=source["system_id"],
        resource_name="scan",
        ingestion_timestamp=INSTANT,
    )

    assert dict(envelope.raw_payload) == {BLOB_PAYLOAD_KEY: encoded}
    assert envelope.observed_time is None


def test_the_envelope_id_is_stable_across_an_unchanged_re_read(
    source: Any, events: Any
) -> None:
    """A polling ingress must not manufacture history (INV-CH7-17).

    Two reads of unchanged content produce one identity, so the graph's
    idempotent upsert and lineage set-union collapse the re-read.
    """
    item = events["envelopes"][0]
    name = item["envelope_id"]

    def mapped() -> SignalEnvelope:
        return to_envelope(
            _text(source, name, item["payload"]),
            tenant_id=source["tenants"]["primary"],
            system_id=source["system_id"],
            resource_name=name,
            ingestion_timestamp=INSTANT,
        )

    assert mapped().envelope_id == mapped().envelope_id
    # And different content is a different signal.
    changed = to_envelope(
        _text(source, name, {**item["payload"], "extra": "1"}),
        tenant_id=source["tenants"]["primary"],
        system_id=source["system_id"],
        resource_name=name,
        ingestion_timestamp=INSTANT,
    )
    assert changed.envelope_id != mapped().envelope_id


# --- malformed content ------------------------------------------------------


def test_malformed_content_raises_naming_which_item_failed(
    source: Any, events: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A silently dropped resource is a graph that is quietly wrong (T-06-25).

    The position is in the message because an acquisition of many items is
    undiagnosable without it.
    """
    item = events["envelopes"][0]
    name = item["envelope_id"]
    resources = {name: _uri(source, name)}
    broken = TextResourceContents(
        uri=_uri(source, name),
        mimeType=source["mime_type"],
        text="{not json at all",
    )
    _stub_reads(
        monkeypatch,
        {
            resources[name]: ReadResourceResult(
                contents=[_text(source, name, item["payload"]), broken]
            )
        },
    )

    with pytest.raises(McpMappingError) as excinfo:
        _drain(
            _adapter(source, resources),
            tenant_id=source["tenants"]["primary"],
        )

    message = str(excinfo.value)
    assert name in message
    assert "content item 1" in message


def test_json_that_is_not_an_object_is_refused(source: Any) -> None:
    """``raw_payload`` is a mapping; a bare list is not a record."""
    contents = TextResourceContents(
        uri=_uri(source, "listy"),
        mimeType=source["mime_type"],
        text="[1, 2, 3]",
    )
    with pytest.raises(McpMappingError, match="JSON object"):
        to_envelope(
            contents,
            tenant_id=source["tenants"]["primary"],
            system_id=source["system_id"],
            resource_name="listy",
            ingestion_timestamp=INSTANT,
        )


# --- the D-23 multi-principal case ------------------------------------------


def test_two_tenants_over_one_adapter_stay_isolated(
    source: Any, events: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tenant isolation holds because tenancy is a per-call argument (D-23).

    One adapter, one MCP source, two principals draining it. This test fails
    if ``tenant_id`` is ever moved to the constructor — the second drain could
    then only re-emit the first tenant's scope, and the disjointness assertion
    below would break. That is the point of asserting disjointness rather than
    just checking each envelope's own field.
    """
    resources = _resources(source, events)
    responses = {
        resources[eid]: ReadResourceResult(
            contents=[_text(source, eid, item["payload"])]
        )
        for eid, item in (
            (item["envelope_id"], item) for item in events["envelopes"]
        )
    }
    _stub_reads(monkeypatch, responses)
    adapter = _adapter(source, resources)

    primary = _drain(adapter, tenant_id=source["tenants"]["primary"])
    secondary = _drain(adapter, tenant_id=source["tenants"]["secondary"])

    assert primary and secondary
    assert {e.tenant_id for e in primary} == {source["tenants"]["primary"]}
    assert {e.tenant_id for e in secondary} == {source["tenants"]["secondary"]}
    # Neither set contains anything scoped to the other principal.
    assert not [e for e in primary if e.tenant_id == source["tenants"]["secondary"]]
    assert not [e for e in secondary if e.tenant_id == source["tenants"]["primary"]]
    # Same source, same content: the payloads agree while the scopes do not,
    # which is what distinguishes isolation from the adapter simply having
    # read different things.
    assert [dict(e.raw_payload) for e in primary] == [
        dict(e.raw_payload) for e in secondary
    ]


def test_tenancy_is_not_constructor_state(source: Any) -> None:
    """The structural half of the isolation claim (INV-CH7-16).

    Asserted on the signature because that is where it is enforced: a
    ``tenant_id`` the constructor accepted could be shared across principals
    no matter how carefully ``envelopes`` were called.
    """
    import inspect

    assert "tenant_id" not in inspect.signature(MCPSourceAdapter).parameters
    envelopes = inspect.signature(MCPSourceAdapter.envelopes)
    assert envelopes.parameters["tenant_id"].kind is inspect.Parameter.KEYWORD_ONLY
    # And it is the ONLY thing the drain takes — no address, ever (T-06-24).
    assert set(envelopes.parameters) == {"self", "tenant_id"}
