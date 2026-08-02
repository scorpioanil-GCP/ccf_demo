"""Session-scoped cross-process server fixture (Phase 11 D-15/D-18/D-20).

Spawns ``examples/04-cross-process/producer_child.py`` — a real ``/runtime``
MCP egress server plus a real A2A/peering endpoint, both bound to ephemeral
ports on 127.0.0.1 — in its own OS process, and yields warm clients so the
benchmarks in this suite time *transport only*.

Reuse rationale (this plan's recorded choice): example 04's child is the
canonical server child — property-intelligence domain values authored fresh
for that example (its D-07/D-08), all loaded from its own ``artifacts/*.yaml``.
Reusing it drags no banking artifacts in and keeps the subprocess wiring in
one place; a perf-local copy would be a second copy of exactly the lifecycle
mechanics ``tests/crossproc/conftest.py`` warns against copying.

Two disciplines are load-bearing (research Pitfall 5; D-15):

* **Readiness is a handshake, never a wait-loop.** The child prints
  ``READY {mcp_port} {a2a_port}`` only once both its servers report started;
  the parent's *blocking* ``readline()`` is the gate. Nothing here polls or
  pauses on a timer.
* **Warm-up precedes yield.** Before any benchmark sees a client, the fixture
  performs :data:`WARMUP_ROUND_TRIPS` real round-trips on EACH transport, so
  import cost, first-connection setup, and lazy-init on either side never
  pollute a timed round.

Teardown is guaranteed: process-group ``SIGTERM`` → ``wait(timeout)`` →
``SIGKILL`` from a ``finally`` (example 04 discipline; threat T-11-10).
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

import httpx
import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_EXAMPLE_04 = _REPO_ROOT / "examples" / "04-cross-process"
_CHILD = _EXAMPLE_04 / "producer_child.py"
_EXAMPLE_ARTIFACTS = _EXAMPLE_04 / "artifacts"

for _root in (_REPO_ROOT / "src", _REPO_ROOT / "runtime"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from ccf.mcp.client import McpResourceClient, SyncMcpBridge  # noqa: E402
from ccf.peering.admission import PRODUCER_ASSERTION_HEADER  # noqa: E402
from ccf.peering.identity import (  # noqa: E402
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
    SignedContextProduct,
)
from ccf.peering.protocol import PeerRef  # noqa: E402
from ccf.products.contract import ContextProductContract  # noqa: E402
from ccf_runtime.mcp.egress import product_uri  # noqa: E402
from ccf_runtime.peering.typed_http import TypedHttpWire  # noqa: E402

#: Warm-up round-trips performed on each transport before the fixture yields
#: (research Pitfall 5: exclude startup/import cost from every timed round).
WARMUP_ROUND_TRIPS = 10

#: Grace given to a terminated child before escalating to SIGKILL.
TERMINATE_TIMEOUT_SECONDS = 10

#: Deadline every synchronous MCP call is bounded by. Lifecycle mechanism
#: values, not domain values.
CALL_TIMEOUT_SECONDS = 20.0


def _load(name: str) -> Any:
    return yaml.safe_load(
        (_EXAMPLE_ARTIFACTS / name).read_text(encoding="utf-8")
    )


def _instant(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


class CrossProcessEndpoints(NamedTuple):
    """Warm clients over a live child process, one per transport."""

    mcp_client: McpResourceClient
    product_address: str
    expected_tenant: str
    expected_schema_name: str
    wire: TypedHttpWire
    peer: PeerRef
    signed: SignedContextProduct
    product: ContextProductContract


@pytest.fixture(scope="session")
def crossproc_endpoints() -> Iterator[CrossProcessEndpoints]:
    """Spawn the real server child; yield warm MCP + peering clients.

    READY-handshake spawn, ≥``WARMUP_ROUND_TRIPS`` warm-ups per transport
    before yield, process-group terminate→wait→kill teardown (D-15).
    """
    ontology = _load("ontology.yaml")
    control = _load("controlplane.yaml")
    federation = _load("a2a.yaml")

    tenant_id: str = ontology["tenant_id"]
    declared_class = control["product_class"]
    consumer_values = federation["consumer"]
    producer_values = federation["producer"]
    now = _instant(control["decision"]["now"])

    proc: subprocess.Popen[bytes] | None = None
    with tempfile.TemporaryDirectory(prefix="ccf-perf-crossproc-") as scratch:
        stderr_path = Path(scratch) / "producer-child.stderr"
        try:
            with stderr_path.open("wb") as stderr_sink:
                # Standalone mode: no consumer URL, so the child assembles,
                # signs with a throwaway key, serves both surfaces, announces.
                proc = subprocess.Popen(
                    [sys.executable, str(_CHILD)],
                    stdout=subprocess.PIPE,
                    stderr=stderr_sink,
                    start_new_session=True,
                )
            assert proc.stdout is not None
            announcement = proc.stdout.readline().decode().strip()
            if not announcement.startswith("READY "):
                captured = stderr_path.read_text(encoding="utf-8")
                raise AssertionError(
                    "producer child did not announce readiness "
                    f"(got {announcement!r}); its stderr was:\n{captured}"
                )
            _token, mcp_port, a2a_port = announcement.split()

            address = product_uri(
                tenant=tenant_id,
                product_class=declared_class["schema_name"],
                version=declared_class["schema_version"],
            )
            with SyncMcpBridge(
                call_timeout_seconds=CALL_TIMEOUT_SECONDS
            ) as bridge, httpx.Client(timeout=CALL_TIMEOUT_SECONDS) as client:
                mcp_client = McpResourceClient(
                    url=f"http://127.0.0.1:{mcp_port}/mcp", bridge=bridge
                )

                # Warm-up round-trips, transport 1 (MCP egress): real reads
                # of the real product, results discarded except the last.
                over_mcp = ""
                for _ in range(WARMUP_ROUND_TRIPS):
                    over_mcp = mcp_client.read_text(address)
                product = ContextProductContract.model_validate_json(over_mcp)

                # This process's own signing identity for the peering leg:
                # a throwaway key, never committed. The wire performs no
                # verification (admission is the gate's job, above every
                # transport), so any well-formed envelope exercises the
                # transport honestly.
                from joserfc.jwk import ECKey  # noqa: PLC0415

                key_id: str = producer_values["key_id"]
                key_dir = Path(scratch) / "keys"
                key_dir.mkdir()
                key = ECKey.generate_key("P-256", parameters={"kid": key_id})
                (key_dir / f"{key_id}.jwk").write_text(
                    json.dumps(key.as_dict(private=True)), encoding="utf-8"
                )
                provider = DetachedJwsIdentityProvider(
                    key_source=FileBackedKeySource(directory=key_dir)
                )
                signed = provider.sign(
                    product=product,
                    key_id=key_id,
                    assertions={
                        PRODUCER_ASSERTION_HEADER: producer_values[
                            "producer_hash"
                        ]
                    },
                )
                wire = TypedHttpWire(
                    local_peer_id=consumer_values["peer_id"],
                    endpoints=lambda *, peer: (
                        f"http://127.0.0.1:{a2a_port}"
                        + consumer_values["receive_path"]
                    ),
                    http_client=client,
                    clock=lambda: now,
                    receive_path=consumer_values["receive_path"],
                    max_request_bytes=consumer_values["max_request_bytes"],
                )
                peer = PeerRef(
                    tenant_id=tenant_id, peer_id=producer_values["peer_id"]
                )

                # Warm-up round-trips, transport 2 (A2A/peering).
                for _ in range(WARMUP_ROUND_TRIPS):
                    wire.emit(peer=peer, signed=signed)

                yield CrossProcessEndpoints(
                    mcp_client=mcp_client,
                    product_address=address,
                    expected_tenant=tenant_id,
                    expected_schema_name=declared_class["schema_name"],
                    wire=wire,
                    peer=peer,
                    signed=signed,
                    product=product,
                )
        finally:
            if proc is not None:
                # Reap the whole process group: the child owns two servers,
                # and an orphaned server holds ports past this session
                # (T-11-10; example 04 discipline).
                group = os.getpgid(proc.pid)
                try:
                    os.killpg(group, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=TERMINATE_TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(group, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait()
                if proc.stdout is not None:
                    proc.stdout.close()
