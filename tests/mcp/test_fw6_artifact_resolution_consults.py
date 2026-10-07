"""FW-6 (whole-branch review M-2): the MCP artifact server's name resolution consults the erasure index (SEC-009; `D-IMPL-374`).

The whole-branch review read it: the blob, presence and names resources of
``ccf_runtime.mcp.artifact_server`` read through the erasure-consulting store,
while the name-resolution resource resolved a versioned URI through the RAW
store. In process, ``ErasureConsultingStore.resolve_uri`` refuses an erased
address; over the §7.4 reference store the same verb answered ``found: true``
and the address — breaking the "swap the store, nothing else changes" parity
CLAUDE.md §7.4 claims.

After the repair the resolution reads the caller's own tenant view of the
consulted store, and an erased address answers the resolution's own not-found
rendering (``found: false``, no address) — so the MCP store client refuses to
resolve it, as the in-process store does.
"""

from __future__ import annotations

import pathlib

import anyio
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var

from ccf.artifacts.protocol import ArtifactStoreError
from ccf.authz.capability import ArtifactWrite
from ccf.erasure import ErasedContentRefused, compose_erasure_consult
from ccf_runtime.mcp.artifact_server import ArtifactResolution
from tests.composition import declared_erasure_trust
from tests.controlplane.capabilities import capability
from tests.erasure import composed
from tests.erasure import harness as h
from tests.mcp import test_artifact_server_authorized as aa
from tests.mcp.test_sec009_artifact_server_erasure import DOCUMENT, _server
from tests.mcp.guarded_servers import TENANT


def _resolution(server: object, uri: str) -> ArtifactResolution:
    reset = aa._as_grant(aa._grant(TENANT))
    try:
        (answer,) = anyio.run(server.read_resource, uri)  # type: ignore[attr-defined]
    finally:
        auth_context_var.reset(reset)
    return ArtifactResolution.model_validate_json(str(answer.content))


def test_an_erased_address_does_not_resolve_over_the_mcp_artifact_server(tmp_path: pathlib.Path) -> None:
    server, store, index, registry = _server(tmp_path)
    ref = store.put(capability(ArtifactWrite, tenant=TENANT, resource="c/n"), DOCUMENT)
    # Positive control: before the erasure the name resolves, with the address.
    before = _resolution(server, ref.uri)
    assert before.found is True and before.content_address == ref.content_address

    composed.erase(store, index, ref.content_address, control_plane=registry, tenant=TENANT)

    # In process, the consulting store refuses to resolve the erased address...
    in_process = compose_erasure_consult(
        store, index=index, audit_log=registry.audit_log, clock=h.fabric_clock,
        control_plane=registry, erasure_trust=declared_erasure_trust(TENANT),
    )
    with pytest.raises(ErasedContentRefused):
        in_process.scoped(TENANT).resolve_uri(uri=ref.uri)
    assert isinstance(ErasedContentRefused(content_address="a", erasure_record_address=None, reason=None, erased_at=None), ArtifactStoreError)

    # ...and over MCP it must not resolve either: not `found: true` and the address.
    after = _resolution(server, ref.uri)
    assert after.found is False, f"the erased address resolved over MCP: {after}"
    assert after.content_address is None
