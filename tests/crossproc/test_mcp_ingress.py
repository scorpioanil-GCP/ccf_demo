"""L1 MCP ingress across a real process boundary (XPRC-01; CLAUDE.md §7.1).

Whitepaper §8.3 Pattern 3, in the direction the whitepaper does not commit —
CLAUDE.md §7.1's "MCP as ingress (L1)". A separate OS process publishes
opaque source records as MCP Resources; this one acquires them with
:class:`~ccf.signal.mcp_source.MCPSourceAdapter`, normalizes them into L1
envelopes, and drives them into the graph through L2 and nothing else.
Nothing is shared but the wire.

Every assertion below is drafted from *what would fail here*:

=========================================  ===================================
Invariant / requirement                    What would fail here
=========================================  ===================================
single-writer (INV-CH7-10, CLAUDE.md §10)  the ingress adapter would name or
                                           hold a graph handle and so have a
                                           route into L3 that bypasses L2;
                                           here every claim in the graph
                                           arrived via ``worker.ingest``, and
                                           the graph is empty until it does
L1 does not interpret (INV-CH7-14)         an ``observed_time`` guessed by the
                                           adapter — from the read, from the
                                           server's ``_meta``, from a payload
                                           field — would appear on envelopes
                                           that crossed a real wire, where a
                                           stubbed transport could not show it
tenant isolation (T-06-26, D-23)           one adapter over one live source
                                           would leak an envelope between two
                                           principals; tenancy being a
                                           per-call argument is what prevents
                                           it, and only a shared source makes
                                           the case real
payload opacity (T-06-25)                  the fabric's vocabulary would
                                           appear in ``raw_payload``, or the
                                           MCP-shaped delivery facts would,
                                           after a real server round trip
readiness discipline (D-16)                a sleep-gated fixture would pass
                                           against a server that never
                                           started; the read happens only
                                           after the child's stdout handshake
one shared client (D-IMPL-13)              the adapter would open a session of
                                           its own; it reaches the live server
                                           only through ``ccf.mcp.client``
=========================================  ===================================

Every domain value comes from ``tests/fixtures/banking/`` by way of the child
and the shared loaders. Delete the fixtures and this file has nothing to
assert (CLAUDE.md §6.4 applied to fixture code).
"""

from __future__ import annotations

import asyncio
import inspect
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.boot import boot
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.mcp.client import McpResourceClient
from ccf.signal.envelope import SignalEnvelope
from ccf.signal.mcp_source import MCPSourceAdapter
from ccf.signal.source import SignalSourceProtocol

from crossproc.servers.mcp_ingress_child import load
from http_api.composition_authority import (
    register_at_composition,
)

pytestmark = pytest.mark.crossproc

CHILD = Path(__file__).resolve().parent / "servers" / "mcp_ingress_child.py"

#: A fixed ingestion instant, injected: an envelope timestamped from a wall
#: clock does not replay.
INSTANT = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)

with_child = pytest.mark.parametrize(
    "child_server_port", [CHILD], indirect=True
)


@pytest.fixture(scope="module")
def source() -> Any:
    return load("mcp_source.yaml")


@pytest.fixture(scope="module")
def events() -> Any:
    return load("events.yaml")


@pytest.fixture(scope="module")
def ontology() -> Any:
    return load("ontology.yaml")


def _resources(source: Any, events: Any) -> dict[str, str]:
    """The deployment's resource selection — its names, and the URIs to read.

    Assembled test-side from the fixture, exactly as a deployment's Control
    Plane configuration would supply it. This is the SSRF boundary in
    practice: nothing the server returns can add to or alter this mapping.
    """
    from crossproc.servers.mcp_ingress_child import resource_uri

    return {
        item["envelope_id"]: resource_uri(source, item["envelope_id"])
        for item in events["envelopes"]
    }


@pytest.fixture
def adapter(loopback_url: str, source: Any, events: Any) -> MCPSourceAdapter:
    """One adapter over the live child, wired the way a deployment would."""
    return MCPSourceAdapter(
        system_id=source["system_id"],
        client=McpResourceClient(url=loopback_url),
        resources=_resources(source, events),
        clock=lambda: INSTANT,
    )


def _drain(
    adapter: MCPSourceAdapter, *, tenant_id: str
) -> tuple[SignalEnvelope, ...]:
    """Run one acquisition to completion, over the real wire.

    ``asyncio.run`` per drain, mirroring ``test_cdc_slice.py``: the async
    surface belongs to ingestion, not to the synchronous fabric core
    (D-IMPL-04(b)).
    """

    async def collect() -> tuple[SignalEnvelope, ...]:
        return tuple([e async for e in adapter.envelopes(tenant_id=tenant_id)])

    return asyncio.run(collect())


# --- the structural claims the module docstring makes -----------------------


def test_the_ingress_modules_hold_no_route_into_the_graph() -> None:
    """Single-writer across the seam: there is no handle here to hand out.

    Asserted against the modules' source because that is where the claim is
    falsifiable — a field, an import, or a parameter naming a graph handle
    shows up here before it could ever show up in behaviour.
    """
    import ccf.signal.mcp_envelope_map as mapping
    import ccf.signal.mcp_source as adapter_module

    for module in (adapter_module, mapping):
        source_text = inspect.getsource(module)
        for forbidden in ("GraphWriter", "GraphReader", "ccf.graph"):
            assert forbidden not in source_text, (
                f"{forbidden} appears in {module.__name__}; an L1 ingress "
                "adapter must hold no route into L3 (INV-CH7-10, T-06-27)"
            )


def test_the_adapter_satisfies_the_ingress_seam_at_runtime(
    source: Any, events: Any
) -> None:
    """Conformance is what the composition root's wiring check relies on."""
    adapter = MCPSourceAdapter(
        system_id=source["system_id"],
        client=McpResourceClient(url="unused://never-dialled"),
        resources=_resources(source, events),
    )
    assert isinstance(adapter, SignalSourceProtocol)


# --- the live acquisition ---------------------------------------------------


@with_child
def test_records_cross_the_process_boundary_into_valid_envelopes(
    adapter: MCPSourceAdapter, source: Any, events: Any
) -> None:
    """A live MCP server's records normalize into L1 envelopes, uninterpreted.

    The three assertions that matter are the ones a stubbed transport could
    not make honestly: the records really came off a socket, the adapter
    really declined to invent an observed time for them, and the identity it
    recorded is the deployment's, not the address it dialled.
    """
    resources = _resources(source, events)
    drained = _drain(adapter, tenant_id=source["tenants"]["primary"])

    # One envelope per *resource*, not per fixture row: ``events.yaml``
    # deliberately repeats an envelope id (the re-delivery case), and a source
    # publishing one record twice under one name is still one record.
    assert len(drained) == len(resources)
    by_resource = {
        envelope.source_metadata["resource_name"]: envelope
        for envelope in drained
    }
    assert set(by_resource) == set(resources)
    for item in events["envelopes"]:
        envelope = by_resource[item["envelope_id"]]
        assert dict(envelope.raw_payload) == item["payload"]
        # MCP states no observed time; L1 does not invent one (INV-CH7-14).
        assert envelope.observed_time is None
        assert envelope.ingestion_timestamp == INSTANT
        assert envelope.source.system_id == source["system_id"]
        assert envelope.tenant_id == source["tenants"]["primary"]
        # The delivery facts are quarantined, not mixed into the payload.
        assert envelope.source_metadata["mimeType"] == source["mime_type"]
        for mcp_key in ("uri", "mimeType", "resource_name"):
            assert mcp_key not in envelope.raw_payload


@with_child
def test_two_tenants_over_one_live_adapter_stay_isolated(
    adapter: MCPSourceAdapter, source: Any
) -> None:
    """The D-23 multi-principal case against a shared, real source.

    One adapter, one server, two principals. Isolation holds because tenancy
    is an argument of the drain rather than constructor state — move it and
    the second drain can only re-emit the first principal's scope, and the
    disjointness assertion below fails.
    """
    primary = _drain(adapter, tenant_id=source["tenants"]["primary"])
    secondary = _drain(adapter, tenant_id=source["tenants"]["secondary"])

    assert primary and secondary
    assert {e.tenant_id for e in primary} == {source["tenants"]["primary"]}
    assert {e.tenant_id for e in secondary} == {source["tenants"]["secondary"]}
    # Same source, same content, different scopes: which is what makes this
    # isolation rather than the adapter having read two different things.
    assert [dict(e.raw_payload) for e in primary] == [
        dict(e.raw_payload) for e in secondary
    ]


@with_child
def test_acquired_signal_reaches_the_graph_only_through_l2(
    adapter: MCPSourceAdapter, source: Any, ontology: Any, tmp_path: Path
) -> None:
    """The single-writer proof, in the shape ``test_cdc_slice`` uses.

    The graph is asserted empty *before* ingestion and populated after, with
    ``worker.ingest`` the only call in between. An adapter that could write
    would make the first assertion fail; an L2 that could be bypassed would
    make the second pass without it.
    """
    # The resolution spec is built by the proto-quickstart's own helper rather
    # than re-implemented, for the reason the egress child gives: a second
    # implementation of the deployment's wiring is a second thing to keep
    # correct, and the two would agree only until one changed.
    from integration.test_proto_quickstart import _resolution_spec

    tenant_id = ontology["tenant_id"]
    control = load("controlplane.yaml")
    keys = control["keys"]
    registry = ControlPlaneRegistry()
    spec_version = register_at_composition(registry, 
        keys["resolution_spec"],
        _resolution_spec(ontology),
    )
    policy_version = register_at_composition(registry, 
        keys["policy_bundle"], control["policy_bundle"]
    )
    handle = boot(
        backend="sqlite",
        connection={"database_path": tmp_path / "mcp-ingress.sqlite3"},
        registry=registry,
        resolution_spec_key=keys["resolution_spec"],
        resolution_spec_version=spec_version,
        policy_bundle_key=keys["policy_bundle"],
        policy_bundle_version=policy_version,
    )
    try:
        boundary = datetime(2100, 1, 1, tzinfo=UTC)
        before = handle.reader.as_of(tenant_id=tenant_id, at=boundary)
        assert not before.entities

        # The only route into L3 — mirroring `_ingest_feed` in the CDC slice.
        drained = _drain(adapter, tenant_id=tenant_id)
        for envelope in drained:
            handle.worker.ingest(envelope)

        after = handle.reader.as_of(tenant_id=tenant_id, at=boundary)
        assert after.entities
        classes = {record.claim.entity_class for record in after.entities}
        assert classes <= {
            rule["entity_class"] for rule in ontology["entity_rules"]
        }
        # Every claim's lineage names an envelope this acquisition produced —
        # nothing entered the graph from anywhere else.
        acquired = {envelope.envelope_id for envelope in drained}
        for record in after.entities:
            assert {entry.envelope_id for entry in record.claim.lineage} <= (
                acquired
            )
            # And the lineage names the *declared* identity, not the address
            # the acquisition dialled (INV-CH8-01).
            assert {entry.source.system_id for entry in record.claim.lineage} == {
                source["system_id"]
            }
    finally:
        handle.close()


@with_child
def test_a_resource_the_server_does_not_publish_fails_rather_than_emitting(
    loopback_url: str, source: Any
) -> None:
    """An absent resource is an error, never an empty acquisition.

    Silently yielding nothing would make a misconfigured selection look like a
    source with no data, which is the same class of quiet wrongness
    :class:`McpMappingError` exists to prevent for malformed content.
    """
    from ccf.mcp.errors import McpServerUnreachable
    from crossproc.servers.mcp_ingress_child import resource_uri

    adapter = MCPSourceAdapter(
        system_id=source["system_id"],
        client=McpResourceClient(url=loopback_url),
        resources={
            source["absent_resource"]: resource_uri(
                source, source["absent_resource"]
            )
        },
        clock=lambda: INSTANT,
    )

    with pytest.raises(McpServerUnreachable):
        _drain(adapter, tenant_id=source["tenants"]["primary"])
