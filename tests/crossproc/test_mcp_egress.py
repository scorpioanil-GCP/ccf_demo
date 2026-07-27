"""The D-01 slice: a Context Product crosses a real process boundary (XPRC-01).

Whitepaper §8.3 Pattern 3; CLAUDE.md §7.1 (MCP egress) and §8.3 (the MCP server
as a v0 front door). The child assembles a banking product through the whole
L1→L6 path and serves it as an MCP Resource; this process reads it back over
loopback HTTP with :mod:`ccf.mcp.client`. Nothing is shared but the wire.

Every assertion below is drafted from *what would fail here*:

=========================================  ===================================
Invariant / requirement                    What would fail here
=========================================  ===================================
single-writer (INV-CH7-10, CLAUDE.md §10)  the egress module would name a graph
                                           write or read handle, or import the
                                           graph package, and so have a route
                                           into L3 to hand a consumer
scheme separation (T-06-16)                an artifact-scheme URI would resolve
                                           at the egress server, making a
                                           live-assembly address look like an
                                           immutable one in a replay record
readiness discipline (D-16)                a sleep-gated fixture would pass
                                           against a server that never started;
                                           here the read happens only after the
                                           child's own stdout handshake
byte fidelity                              the product would arrive re-encoded,
                                           and a consumer hashing what it got
                                           would compute a different address
tenant addressing (T-06-13)                a product would be served under a
                                           tenant it was not assembled for
sync bridge liveness (B3, T-06-15)         a regression to the held-session
                                           bridge would hang; the bounded call
                                           fails fast instead
=========================================  ===================================

Every domain value — tenant, product class, schema version — comes from
``tests/fixtures/banking/`` by way of the child's builder. Delete the fixtures
and this file has nothing to assert (CLAUDE.md §6.4 applied to fixture code).
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.mcp.client import McpResourceClient, SyncMcpBridge
from ccf.mcp.errors import McpServerUnreachable

from crossproc.servers.mcp_egress_child import (
    ProductAddress,
    build_servable_product,
)

pytestmark = pytest.mark.crossproc

CHILD = Path(__file__).resolve().parent / "servers" / "mcp_egress_child.py"

#: Deadline every synchronous call is bounded by. Generous enough for a cold
#: child, short enough that the deadlocking bridge fails the suite in seconds
#: instead of hanging CI until its own timeout (06-RESEARCH.md B3).
CALL_TIMEOUT_SECONDS = 20.0

with_child = pytest.mark.parametrize(
    "child_server_port", [CHILD], indirect=True
)


@pytest.fixture
def expected(tmp_path: Path) -> tuple[str, ProductAddress]:
    """The product this process independently assembles, and its address.

    Recomputed here rather than trusted from the wire: comparing what arrived
    against what the fabric produces is the only version of this assertion that
    can fail for the right reason. Assembly is deterministic for a fixed
    boundary (proved in ``test_proto_quickstart``), so the two processes must
    agree byte for byte.
    """
    assembled = build_servable_product(
        database_path=tmp_path / "egress-parent.sqlite3"
    )
    return canonical_bytes(assembled.servable.product).decode("utf-8"), (
        assembled.address
    )


@pytest.fixture
def bridge() -> Iterator[SyncMcpBridge]:
    """One bounded sync bridge per test, closed on teardown."""
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
        yield bridge


# --- the structural claim the module docstring makes -----------------------


def test_the_egress_module_holds_no_route_into_the_graph() -> None:
    """Single-writer across the seam: there is no handle here to hand out.

    Asserted against the module's source because that is where the claim is
    falsifiable. A field, an import, or a parameter naming a graph handle would
    show up here before it could ever show up in behaviour.
    """
    import ccf_runtime.mcp.egress as egress

    source = inspect.getsource(egress)
    for forbidden in ("GraphWriter", "GraphReader", "ccf.graph"):
        assert forbidden not in source, (
            f"{forbidden} appears in the egress server's source; the L6 egress "
            "seam must hold no route into L2 or L3 (INV-CH7-10, T-06-12)"
        )


def test_the_egress_scheme_is_not_the_artifact_scheme() -> None:
    """Live products and artifacts at rest are addressed differently (T-06-16).

    A shared scheme would let a TTL-bound, assembled-now URI be recorded as if
    it named a content-addressed artifact — a replay would then resolve
    something that no longer exists, or worse, something different.
    """
    from ccf.artifacts.protocol import ARTIFACT_URI_SCHEME
    from ccf_runtime.mcp.egress import PRODUCT_URI_SCHEME

    assert PRODUCT_URI_SCHEME != ARTIFACT_URI_SCHEME


# --- the cross-process round trip ------------------------------------------


@with_child
def test_the_product_crosses_the_process_boundary_intact(
    loopback_url: str, expected: tuple[str, ProductAddress], bridge: SyncMcpBridge
) -> None:
    """A separate OS process serves the product; this one reads it back.

    The comparison is on canonical bytes, so a re-encode anywhere on the path —
    key reordering, float reformatting, a timestamp losing its offset — fails
    here rather than surfacing later as a content address that does not match.
    """
    canonical, address = expected
    client = McpResourceClient(url=loopback_url, bridge=bridge)

    received = client.read_text(address.uri)

    assert received == canonical
    # And it is a real product, not an opaque blob that happens to match.
    payload = json.loads(received)
    assert payload["tenant_id"] == address.tenant
    assert payload["schema_name"] == address.product_class
    assert payload["lineage"]["operators_invoked"]


@with_child
def test_the_server_advertises_the_product_resource(
    loopback_url: str, expected: tuple[str, ProductAddress], bridge: SyncMcpBridge
) -> None:
    """Discovery works over the wire and speaks the CCF scheme.

    A consumer that cannot list is a consumer that must be told the URI out of
    band, which defeats Pattern 3's "without knowing anything about the
    fabric's internals".
    """
    from ccf_runtime.mcp.egress import PRODUCT_URI_TEMPLATE, PRODUCT_URI_SCHEME

    _canonical, _address = expected
    client = McpResourceClient(url=loopback_url, bridge=bridge)

    templates = client.resource_templates()

    # Templated, not enumerated: the fabric advertises the shape of what it can
    # assemble, because listing every product it *could* assemble would mean
    # assembling them, and a discovery call must not run the fabric.
    assert PRODUCT_URI_TEMPLATE in templates
    assert all(uri.startswith(f"{PRODUCT_URI_SCHEME}://") for uri in templates)
    assert client.resource_uris() == ()


@with_child
def test_a_foreign_address_is_refused_rather_than_served(
    loopback_url: str, expected: tuple[str, ProductAddress], bridge: SyncMcpBridge
) -> None:
    """The wrong tenant does not get the right product (T-06-13).

    Without this the round-trip test would pass against a resolver that ignored
    its arguments entirely, and cross-tenant leakage would be untested.
    """
    _canonical, address = expected
    foreign = ProductAddress(
        tenant=f"{address.tenant}-not-this-one",
        product_class=address.product_class,
        version=address.version,
    )
    client = McpResourceClient(url=loopback_url, bridge=bridge)

    with pytest.raises(McpServerUnreachable):
        client.read_text(foreign.uri)


@with_child
def test_the_sync_bridge_completes_from_a_synchronous_test_body(
    loopback_url: str, expected: tuple[str, ProductAddress]
) -> None:
    """Three bounded sync calls, no event loop in sight, no hang (B3).

    Every call above already goes through the bridge; this one exists to make
    the *repeat* case explicit. The held-session bridge that deadlocks survived
    a single call in prototyping and hung on reuse, so one call is not the
    assertion that would have caught it.
    """
    canonical, address = expected
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
        client = McpResourceClient(url=loopback_url, bridge=bridge)
        results = [client.read_text(address.uri) for _ in range(3)]
    assert results == [canonical] * 3


def test_a_sync_client_without_a_bridge_refuses_rather_than_improvises() -> None:
    """No background thread is manufactured behind the caller's back.

    A client that spun up its own loop on demand would own a thread nobody
    closes, which is how a test suite ends with more threads than tests.
    """
    client = McpResourceClient(url="http://127.0.0.1:1/mcp")
    with pytest.raises(McpServerUnreachable):
        client.resource_uris()


# --- the fixture's own failure mode ----------------------------------------


def test_a_child_that_dies_at_import_fails_with_its_stderr(tmp_path: Path) -> None:
    """A crashing child produces a diagnosis, not ``int('')`` (fixture hardening).

    This is the fixture's own regression test: the readiness gate is a blocking
    ``readline()``, and the empty-line case is exactly where a naive
    implementation raises something that says nothing about the child.
    """
    from crossproc.conftest import spawn_child_server

    broken = tmp_path / "broken_child.py"
    broken.write_text("raise SystemExit('deliberate child import failure')\n")

    with pytest.raises(AssertionError, match="deliberate child import failure"):
        with spawn_child_server(broken):
            pass
