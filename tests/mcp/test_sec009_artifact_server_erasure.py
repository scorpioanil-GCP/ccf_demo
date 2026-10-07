"""SEC-009 — the MCP artifact server serves the erased reading, never erased bytes (`D-IMPL-374` (4)).

Coordinator ruling on the MCP artifact server: it is the ArtifactStore's
persistence transport (CLAUDE.md §7.4), so it composes the erasure consult
itself, over a REQUIRED ``control_plane`` constructor parameter, through
``compose_erasure_consult``.

RED today: the server has no Control Plane to consult, so a client-lane
artifact whose erasure is mirrored is served — its bytes cross.
"""

from __future__ import annotations

import inspect
import pathlib
from typing import Any

from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

from ccf.authz.capability import ArtifactWrite
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.refusal import RefusalEnvelope
from ccf_runtime.mcp.artifact_server import build_artifact_server
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource
from tests.controlplane.capabilities import capability
from tests.erasure import composed
from tests.http_api.composition_authority import deployment_store, refusal_recorder
from tests.mcp import test_artifact_server_authorized as aa
from tests.mcp.guarded_servers import (
    REPLAY_RECORD_CLASS,
    SCOPE,
    TENANT,
    _entitlement_world,
    authorizer_granting,
)

NOWHERE = "e" * 64
DOCUMENT = {"customer": {"id": "customer-42"}, "note": "kyc"}


def _server(tmp_path: pathlib.Path, *, level: str | None = None) -> tuple[Any, Any, ControlPlaneRegistry]:
    registry = ControlPlaneRegistry()
    source, recorder = _entitlement_world(tmp_path)
    if level is not None:
        recorder = refusal_recorder(
            registry,
            store=deployment_store(tmp_path / "replay-full", REPLAY_RECORD_CLASS),
            tenant=TENANT,
            replay_record_class=REPLAY_RECORD_CLASS,
            disclosure_level_for=lambda *, tenant, principal_id: (level, None),
        )
    store = deployment_store(tmp_path / "artifacts", REPLAY_RECORD_CLASS)
    arguments: dict[str, Any] = dict(
        server_name="sec009-artifact",
        store=store,
        token_verifier=SourceBackedTokenVerifier(source=StaticTokenSource(grants={"tok": aa._grant(TENANT)})),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://artifact.invalid/mcp"),
            required_scopes=[SCOPE],
        ),
        authorizer=authorizer_granting(),
        entitlement_source=source,
        refusal_recorder=recorder,
        audit_log=registry.audit_log,
    )
    if "control_plane" in inspect.signature(build_artifact_server).parameters:
        arguments["control_plane"] = registry
    return build_artifact_server(**arguments), store, registry


def _shell(payload: bytes) -> RefusalEnvelope:
    return RefusalEnvelope.model_validate_json(payload.decode("utf-8"))


def test_an_erased_artifact_is_not_served_over_the_mcp_artifact_server(tmp_path: pathlib.Path) -> None:
    server, store, registry = _server(tmp_path)
    ref = store.put(capability(ArtifactWrite, tenant=TENANT, resource="c/n"), DOCUMENT)
    assert aa._blob(server, ref.content_address, TENANT) == canonical_bytes(DOCUMENT)
    composed.erase(registry, ref.content_address)
    served = aa._blob(server, ref.content_address, TENANT)
    assert served != canonical_bytes(DOCUMENT), "the erased bytes crossed the MCP artifact server"
    # minimal: the not-found rendering, identical to an address nothing is stored at.
    assert aa._same_shell(_shell(served), _shell(aa._blob(server, NOWHERE, TENANT)))


def test_an_erased_artifact_reads_as_erased_content_above_minimal(tmp_path: pathlib.Path) -> None:
    server, store, registry = _server(tmp_path, level="full")
    ref = store.put(capability(ArtifactWrite, tenant=TENANT, resource="c/n"), DOCUMENT)
    composed.erase(registry, ref.content_address)
    shell = _shell(aa._blob(server, ref.content_address, TENANT))
    assert shell.kind == "erased-content" and shell.disclosure == "full"
    assert shell.fields["erasure_record_address"] == '"' + "f" * 64 + '"'
