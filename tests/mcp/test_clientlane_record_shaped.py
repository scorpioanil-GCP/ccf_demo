"""Record-shaped bytes on the MCP client lane are not served as a client artifact (the client-lane ruling, ``D-IMPL-378``).

The forged-record provenance check (``D-IMPL-376`` close-out) confined the
governed read, :func:`~ccf_runtime.authz.delivery_boundary.govern_dereference`,
to records the fabric's own record writer filed. The MCP artifact server's
client lane (:func:`~ccf_runtime.mcp.artifact_server.build_artifact_server`)
still served a tenant's own client-lane filings to every principal of that
tenant as the exact stored bytes, whatever their shape. Bytes a principal filed
there, shaped as another principal's Decision Replay record, crossed the blob
and presence resources exactly as a governed record the reader may read does:
the same raw canonical bytes, the same ``{"found": true}``. And every SDK
reader of the MCP-backed store took them as a record: the replay engine's read
path, the refusal reconstruction, which verified a forged copy, and the child
admission's record read.

Dave's ruling: such bytes may remain ordinary client artifacts only if their
untrusted origin is explicit and consumers cannot accept them as governed
evidence; otherwise that path is refused until provenance is enforced. Neither
held, so the split decides client-lane bytes that validate as a
:class:`~ccf.replay.record.DecisionReplayRecord` (``model_validate_json``, the
validator :func:`~ccf.replay.engine.resolve_artifact` and every SDK record
reader apply) through the governed dereference. Its provenance check answers
them exactly as a missing address. Every other client-lane artifact is served as
before.

Each test drives a consumer through the shipped
:class:`~ccf.artifacts.mcp_store.McpArtifactStore`, connected in-process to the
shipped server over the shipped file store, and asserts the refusal by its
mechanism: the server's audit trail shows the read decided by the governed
dereference (class :data:`~ccf_runtime.authz.delivery_boundary.DEREFERENCE_PRODUCT_ID`,
``resolved=False``), and no client-lane serve (an event under the client class).

Tenant, principal, class, scope and token names are test deployment
vocabulary, meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import base64
import json
import pathlib
import types
from dataclasses import dataclass
from typing import Any

import anyio
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.types import BlobResourceContents, TextResourceContents
from pydantic import AnyHttpUrl, ValidationError

import ccf.artifacts.mcp_store as mcp_store_module
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.mcp_store import McpArtifactStore
from ccf.artifacts.protocol import ArtifactName, ArtifactNotFound, artifact_uri
from ccf.authz.capability import ArtifactWrite
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.audit import AuditLog, AuthzDecisionAuditEvent
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.child_resolver import GrantBoundChildResolver
from ccf.products.entitlement import PRODUCT_ENTITLEMENT_POLICY, product_entitlement_key
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.engine import (
    RefusalReplayOutcome,
    ReplayUnresolvable,
    replay_refusal,
    resolve_artifact,
    resolve_artifact_at_uri,
)
from ccf.replay.record import DecisionReplayRecord
from ccf_runtime.authz.delivery_boundary import DEREFERENCE_PRODUCT_ID
from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource
from ccf_runtime.mcp.artifact_server import (
    artifact_blob_uri,
    artifact_meta_uri,
    artifact_names_uri,
    build_artifact_server,
)
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource
from tests.composition import declared_erasure_trust, no_erasures
from tests.controlplane.capabilities import capability
from tests.http_api.composition_authority import (
    deployment_store,
    refusal_recorder,
    register_typed_at_composition,
)
from tests.mcp.guarded_servers import (
    AUDIT_INSTANT,
    FOREIGN,
    PRINCIPAL,
    REPLAY_RECORD_CLASS,
    SCOPE,
    TENANT,
    authorizer_granting,
)
from tests.mcp.test_artifact_server_authorized import _as_grant
from tests.mcp.test_c2_tenant_hold_mcp import _file, _grant, _policy, _record
from tests.mcp.test_sec009_mcp_names_at import _Run

#: A client-lane class: one the substrate does not declare governed.
CLIENT_CLASS = "c"

#: Another principal of the reader's own tenant, whom the forged records name.
VICTIM = "clientlane-victim-principal"

#: The three worlds C8 says a tenant's answers must not be able to tell apart.
WORLDS = ("no-other-filing", "other-tenant-client-lane", "other-tenant-governed")


@dataclass
class _World:
    server: FastMCP
    store: FileArtifactStore
    recorded: FileArtifactStore
    registry: ControlPlaneRegistry
    audit_log: AuditLog


def _world(tmp_path: pathlib.Path) -> _World:
    """``tests/mcp/test_c2_tenant_hold_mcp.py::_world``, keeping the server's audit log in hand."""
    registry = ControlPlaneRegistry()
    register_typed_at_composition(
        registry, product_entitlement_key(tenant_id=TENANT), _policy(TENANT), PRODUCT_ENTITLEMENT_POLICY
    )
    source = ControlPlaneProductEntitlementSource(control_plane=registry, clock=lambda: AUDIT_INSTANT)
    recorded = deployment_store(tmp_path / "replay", REPLAY_RECORD_CLASS)
    recorder = refusal_recorder(
        registry,
        store=recorded,
        tenant=TENANT,
        replay_record_class=REPLAY_RECORD_CLASS,
        assembly_mode="algorithmic",
        policy_bundle_pin=None,
        disclosure_level_for=source.disclosure_level_for,
    )
    store = deployment_store(tmp_path / "artifacts", REPLAY_RECORD_CLASS)
    audit_log = ControlPlaneRegistry().audit_log
    server = build_artifact_server(
        server_name="clientlane-record-shaped",
        store=store,
        token_verifier=SourceBackedTokenVerifier(source=StaticTokenSource(grants={"tok": _grant()})),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://artifact.invalid/mcp"),
            required_scopes=[SCOPE],
        ),
        authorizer=authorizer_granting(tenants=(TENANT, FOREIGN)),
        entitlement_source=source,
        refusal_recorder=recorder,
        audit_log=audit_log,
        erasure_trust=declared_erasure_trust(),
        erasure_index=no_erasures(),
        control_plane=ControlPlaneRegistry(),
    )
    return _World(server=server, store=store, recorded=recorded, registry=registry, audit_log=audit_log)


class _Session:
    """An MCP client session answered by the in-process server, as ``PRINCIPAL`` of ``TENANT``."""

    def __init__(self, server: FastMCP) -> None:
        self._server = server

    async def read_resource(self, uri: Any) -> Any:
        reset = _as_grant(_grant())
        try:
            contents = list(await self._server.read_resource(str(uri)))
        finally:
            auth_context_var.reset(reset)
        return types.SimpleNamespace(
            contents=[
                BlobResourceContents(uri=str(uri), blob=base64.b64encode(c.content).decode("ascii"), mimeType=c.mime_type)
                if isinstance(c.content, bytes)
                else TextResourceContents(uri=str(uri), text=c.content, mimeType=c.mime_type)
                for c in contents
            ]
        )


def _client(world: _World, monkeypatch: pytest.MonkeyPatch) -> McpArtifactStore:
    """The shipped MCP-backed store, its sessions answered by ``world``'s server."""
    session = _Session(world.server)

    async def run_with_session(*, url: str, operation: Any, http_client_factory: Any) -> Any:
        return await operation(session)

    monkeypatch.setattr(mcp_store_module, "run_with_session", run_with_session)
    return McpArtifactStore(
        url="http://artifact.invalid/mcp",
        bridge=_Run(),  # type: ignore[arg-type]
        write_kinds=world.store.write_kinds,
    )


def _read(world: _World, uri: str) -> bytes:
    """One resource's answer as the exact bytes that crossed, read as ``PRINCIPAL``."""
    reset = _as_grant(_grant())
    try:
        (answer,) = list(anyio.run(world.server.read_resource, uri))
    finally:
        auth_context_var.reset(reset)
    content = answer.content
    return content if isinstance(content, bytes) else content.encode("utf-8")


def _on_client_lane(world: _World, document: Any, *, name: str) -> str:
    """A principal of ``TENANT`` files ``document`` on its tenant's client lane: an ordinary ``ArtifactWrite``."""
    filed = world.store.put(capability(ArtifactWrite, tenant=TENANT, resource=f"{CLIENT_CLASS}/{name}"), document)
    return str(filed.content_address)


def _forge(world: _World, record: DecisionReplayRecord, *, name: str) -> str:
    """The canonical bytes of ``record``, filed on ``TENANT``'s client lane."""
    return _on_client_lane(world, json.loads(canonical_bytes(record)), name=name)


def _trail(world: _World, address: str, since: int) -> list[tuple[str | None, bool]]:
    """``(class, resolved)`` of every ``authz_decision`` the server appended for ``address`` since ``since``."""
    return [
        (event.artifact_class, event.resolved)
        for event in world.audit_log.events()[since:]
        if isinstance(event, AuthzDecisionAuditEvent) and event.key == address
    ]


def test_the_replay_engines_read_does_not_accept_a_record_shaped_client_lane_filing(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``resolve_artifact`` and ``resolve_artifact_at_uri``, the replay plane's
    one read path and the first step of ``replay`` and ``replay_refusal``, over
    the MCP-backed store: bytes shaped as another principal's record, filed on
    the reader's own tenant's client lane, are not resolved as a record, and the
    store reports them absent. Each read was decided by the governed dereference
    and refused. Controls: the record the fabric's writer filed for the reader
    still resolves, and an ordinary client artifact still crosses as its exact
    bytes, served by the client lane."""
    world = _world(tmp_path)
    client = _client(world, monkeypatch)
    forged = _record(tenant=TENANT, principal=VICTIM, subject="clientlane-forgery")
    address = _forge(world, forged, name="innocuous")
    assert address == content_hash(forged)

    since = len(world.audit_log.events())
    assert client.exists(content_address=address) is False
    with pytest.raises(ReplayUnresolvable):
        resolve_artifact(store=client, content_address=address, contract=DecisionReplayRecord)
    with pytest.raises(ReplayUnresolvable):
        resolve_artifact_at_uri(
            store=client,
            uri=artifact_uri(
                tenant_id=TENANT, artifact_class=CLIENT_CLASS, name="innocuous", artifact_version=address
            ),
            contract=DecisionReplayRecord,
        )
    assert _trail(world, address, since) == [(DEREFERENCE_PRODUCT_ID, False)] * 3, (
        "each read was decided by the governed dereference and refused, never served by the client lane"
    )

    genuine = _record(tenant=TENANT, principal=PRINCIPAL, subject="clientlane-genuine")
    resolved = resolve_artifact(store=client, content_address=_file(world, genuine), contract=DecisionReplayRecord)
    assert (resolved.tenant_id, resolved.perspective_conditioning.principal_id) == (TENANT, PRINCIPAL)
    plain = {"note": "an ordinary client-lane artifact"}
    plain_address = _on_client_lane(world, plain, name="plain")
    since = len(world.audit_log.events())
    assert client.get(content_address=plain_address) == canonical_bytes(plain)
    assert _trail(world, plain_address, since) == [(CLIENT_CLASS, True)]


def test_replay_refusal_does_not_verify_a_forged_refusal_record_from_the_client_lane(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The refusal reconstruction verifies a refusal recorded before any fabric
    read without re-executing anything, so it was the shortest path from a forged
    record to a verified one. A genuine refusal record (the door's own, for the
    reader's read of an empty address), filed by the record writer, verifies over
    the MCP-backed store. A copy naming another principal, filed on the reader's
    tenant's client lane, does not resolve: the governed dereference refused it."""
    world = _world(tmp_path)
    client = _client(world, monkeypatch)
    shell = RefusalEnvelope.model_validate_json(_read(world, artifact_blob_uri(content_address="0" * 64)))
    genuine = DecisionReplayRecord.model_validate_json(
        world.recorded.get(content_address=world.recorded.resolve_uri(uri=shell.replay_reference))
    )
    genuine_address = _file(world, genuine)
    verified = replay_refusal(
        record_address=genuine_address,
        store=client,
        reader=None,  # type: ignore[arg-type]  # a refusal recorded before any read re-executes nothing
        control_plane=world.registry,
        environment=None,  # type: ignore[arg-type]
    )
    assert isinstance(verified, RefusalReplayOutcome)
    assert verified.record.perspective_conditioning.principal_id == PRINCIPAL

    forged = genuine.model_copy(
        update={
            "perspective_conditioning": genuine.perspective_conditioning.model_copy(update={"principal_id": VICTIM})
        }
    )
    address = _forge(world, forged, name="refusal-copy")
    since = len(world.audit_log.events())
    with pytest.raises(ReplayUnresolvable):
        replay_refusal(
            record_address=address,
            store=client,
            reader=None,  # type: ignore[arg-type]
            control_plane=world.registry,
            environment=None,  # type: ignore[arg-type]
        )
    assert _trail(world, address, since) == [(DEREFERENCE_PRODUCT_ID, False)]


def _child_record(base: DecisionReplayRecord, child: Any, touched: tuple[str, ...]) -> DecisionReplayRecord:
    """``base`` describing ``child`` and claiming to have read ``touched``."""
    return base.model_copy(
        update={
            "content_generation_path": base.content_generation_path.model_copy(
                update={"product_content_address": content_hash(child)}
            ),
            "context_fabric_snapshot": base.context_fabric_snapshot.model_copy(update={"touched_entities": touched}),
        }
    )


def test_child_admission_does_not_read_a_client_lane_record_as_the_childs_record(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``GrantBoundChildResolver._touched_entities`` establishes a child's
    eligibility from the record its replay reference names. Over the MCP-backed
    store, a replay reference naming a record-shaped client-lane filing reads as
    absent rather than as the child's record. The control: a record the fabric's
    writer filed answers its touched entities. The method reads only
    ``self._store``, so it is driven with that alone."""
    world = _world(tmp_path)
    client = _client(world, monkeypatch)
    child = {"child": "the product a producer reported"}
    reader = types.SimpleNamespace(_store=client)

    forged = _child_record(_record(tenant=TENANT, principal=VICTIM, subject="clientlane-child"), child, ("forged:entity",))
    address = _forge(world, forged, name="child-record")
    replay_ref = artifact_uri(tenant_id=TENANT, artifact_class=CLIENT_CLASS, name="child-record", artifact_version=address)
    since = len(world.audit_log.events())
    with pytest.raises(ArtifactNotFound):
        GrantBoundChildResolver._touched_entities(reader, replay_ref, child)  # type: ignore[arg-type]
    assert _trail(world, address, since) == [(DEREFERENCE_PRODUCT_ID, False)]

    genuine = _child_record(_record(tenant=TENANT, principal=PRINCIPAL, subject="clientlane-child"), child, ("genuine:entity",))
    genuine_ref = artifact_uri(
        tenant_id=TENANT, artifact_class=REPLAY_RECORD_CLASS, name="record", artifact_version=_file(world, genuine)
    )
    assert GrantBoundChildResolver._touched_entities(reader, genuine_ref, child) == ("genuine:entity",)  # type: ignore[arg-type]


@pytest.mark.parametrize("variant", ["one-extra-key", "one-key-missing"])
def test_record_shaped_means_the_record_validator_accepts_the_bytes_not_a_resemblance(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    """The rule is keyed on ``DecisionReplayRecord.model_validate_json``, the
    validator every SDK record reader applies, never on a resemblance. Bytes one
    key away from a record, which that validator refuses, stay an ordinary client
    artifact: served exactly, by the client lane. The exact record's bytes, on the
    same lane, are refused."""
    world = _world(tmp_path)
    client = _client(world, monkeypatch)
    record = _record(tenant=TENANT, principal=VICTIM, subject="clientlane-near-miss")
    document = json.loads(canonical_bytes(record))
    if variant == "one-extra-key":
        document["not_a_record_field"] = "near-miss"
    else:
        del document["tenant_id"]
    with pytest.raises(ValidationError):
        DecisionReplayRecord.model_validate_json(canonical_bytes(document))

    near = _on_client_lane(world, document, name="near-miss")
    since = len(world.audit_log.events())
    assert client.get(content_address=near) == canonical_bytes(document)
    assert _trail(world, near, since) == [(CLIENT_CLASS, True)]

    exact = _forge(world, record, name="exact")
    since = len(world.audit_log.events())
    with pytest.raises(ArtifactNotFound):
        client.get(content_address=exact)
    assert _trail(world, exact, since) == [(DEREFERENCE_PRODUCT_ID, False)]


def test_a_tenants_answers_for_its_record_shaped_filing_do_not_depend_on_another_tenants_filing(
    tmp_path: pathlib.Path,
) -> None:
    """C8 (``D-IMPL-376`` (6)) holds for record-shaped bytes. Tenant A files, on
    its client lane, the bytes of a record of tenant B; B files the same bytes
    nowhere, on its own client lane, or through its record writer. A's blob,
    presence and names answers are byte-identical across the three worlds. The
    names answer is A's own filing and nothing of B's; blob and presence are the
    governed refusal, the same whether or not B's writer filed the record."""
    record = _record(tenant=FOREIGN, principal=PRINCIPAL, subject="clientlane-c8")
    address = content_hash(record)
    surfaces = {
        "blob": artifact_blob_uri(content_address=address),
        "meta": artifact_meta_uri(content_address=address),
        "names": artifact_names_uri(content_address=address),
    }
    answers: dict[str, dict[str, bytes]] = {}
    for kind in WORLDS:
        (tmp_path / kind).mkdir()
        world = _world(tmp_path / kind)
        assert _forge(world, record, name="mine") == address
        if kind == "other-tenant-client-lane":
            world.store.put(
                capability(ArtifactWrite, tenant=FOREIGN, resource=f"{CLIENT_CLASS}/theirs"),
                json.loads(canonical_bytes(record)),
            )
        elif kind == "other-tenant-governed":
            assert _file(world, record) == address  # B's record writer, under B
        answers[kind] = {surface: _read(world, uri) for surface, uri in surfaces.items()}

    for surface in surfaces:
        by_world = {kind: answers[kind][surface] for kind in WORLDS}
        assert len(set(by_world.values())) == 1, (
            f"{surface}: tenant A's answer depends on another tenant's filing: "
            + "; ".join(f"{kind}={value[:100]!r}" for kind, value in by_world.items())
        )
    assert [ArtifactName.model_validate(item) for item in json.loads(answers["no-other-filing"]["names"])] == [
        ArtifactName(tenant_id=TENANT, artifact_class=CLIENT_CLASS, name="mine", artifact_version=address)
    ]
    assert answers["no-other-filing"]["blob"] != canonical_bytes(record), "the record's bytes crossed the client lane"
    RefusalEnvelope.model_validate_json(answers["no-other-filing"]["meta"])
