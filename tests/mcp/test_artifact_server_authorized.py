"""The artifact server under the capability (``D-IMPL-353`` §1.2, §2 P5).

Every body on ``build_artifact_server`` receives an ``Authorized`` minted by
the wrapper for its declared action and hands it — and nothing else it could
have chosen — to the handle it acts through: ``put_artifact`` to
``store.put(authorized, artifact)``, the blob and presence resources to
``govern_dereference(authorized, ...)``. The ``tenant_id`` tool argument is
gone; the tenant is the capability's.

**Two evidence classes, kept apart on purpose.** The *contract* tests drive a
recording store and a recording dereference that implement the §1.2 shapes
today, so the body's obligations are measured now: which kind, which resource,
which tenant, which arguments. The *real-path* tests drive the shipped
``FileArtifactStore`` and the shipped ``govern_dereference``, whose §1.2
signatures belong to Lane HANDLES and Lane CAP-GATE; they are marked
``xfail(strict=True)`` naming the join, so they turn into a failure the moment
the join lands with the marker still on — the evidence stays executable and is
never weakened into a passing assertion (``D-IMPL-261``).

Tenant, principal, class, scope and token names are test deployment
vocabulary, meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import base64
import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, cast

import anyio
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef, artifact_uri
from ccf.authz.actions import ACTION_ARTIFACT_READ, ACTION_ARTIFACT_WRITE
from ccf.authz.capability import (
    ArtifactRead,
    ArtifactWrite,
    Authorized,
    CapabilityBypassError,
    verify,
)
from ccf.authz.decision import AuthzDecision
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.refusal import (
    RefusalEnvelope,
    RequestIdentity,
    SubjectUnavailableRefusal,
    envelope_for,
)
from ccf.replay.record import DecisionReplayRecord
from ccf_runtime.authz.delivery_boundary import (
    SURFACE_MCP_RESOURCE,
    DereferencedEvidence,
    DereferenceRequest,
)
from ccf_runtime.http_api.errors import ERROR_EVIDENCE_ABSENT
from ccf_runtime.mcp import artifact_server as module
from ccf_runtime.mcp import tenancy
from ccf_runtime.mcp.artifact_server import (
    ARTIFACT_URI_SCHEME,
    BLOB_URI_TEMPLATE,
    META_URI_TEMPLATE,
    NAME_URI_TEMPLATE,
    PUT_ARTIFACT_TOOL,
    ArtifactPresence,
    ArtifactResolution,
    NonCanonicalPayload,
    artifact_blob_uri,
    artifact_meta_uri,
    build_artifact_server,
)
from ccf_runtime.mcp.auth import (
    SourceBackedTokenVerifier,
    StaticTokenSource,
    TokenGrant,
    tenant_claims,
)
from ccf_runtime.mcp.tenancy import (
    ActionUnauthorizedRefused,
    AmbiguousTenantRefused,
    CrossTenantRefused,
    TenantGuardedServer,
    TenantGuardViolation,
)
from tests.mcp.guarded_servers import (
    FOREIGN,
    PRINCIPAL,
    SCOPE,
    TENANT,
    _entitlement_world,
    authorizer_granting,
)

ADDRESS = "a" * 64
JOIN = (
    "join: awaits Lane HANDLES' `ArtifactStoreProtocol.put(authorized, artifact)`"
    " and Lane CAP-GATE's `govern_dereference(authorized, ...)` (D-IMPL-353 §1.2)"
)


# --- fixtures ---------------------------------------------------------------


def _grant(*tenants: str) -> TokenGrant:
    return TokenGrant(client_id=PRINCIPAL, scopes=(SCOPE,), tenants=frozenset(tenants))


def _as_grant(grant: TokenGrant) -> Any:
    return auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="in-process",
                client_id=grant.client_id,
                scopes=list(grant.scopes),
                claims=dict(tenant_claims(grant)),
            )
        )
    )


def _refusal(operation: Any) -> BaseException:
    try:
        operation()
    except BaseException as raised:  # noqa: BLE001 - the subject under test
        seen: list[BaseException] = []
        current: BaseException | None = raised
        while current is not None and current not in seen:
            if isinstance(
                current, (TenantGuardViolation, CapabilityBypassError, NonCanonicalPayload)
            ):
                return current
            seen.append(current)
            current = current.__cause__ or current.__context__
        return raised
    raise AssertionError("the call was served; no refusal to inspect")


@dataclass
class _RecordingStore:
    """A store implementing the §1.2 write shape today, over a real file store
    for the reads the naming resource still makes."""

    inner: FileArtifactStore
    puts: list[tuple[object, object]] = field(default_factory=list)

    def put(self, authorized: object, artifact: object) -> ArtifactRef:
        self.puts.append((authorized, artifact))
        tenant = getattr(authorized, "tenant")
        resource = getattr(authorized, "resource")
        artifact_class, name = str(resource).split("/", 1)
        return ArtifactRef(
            content_address=content_hash(artifact),
            uri=artifact_uri(
                tenant_id=tenant,
                artifact_class=artifact_class,
                name=name,
                artifact_version="1",
            ),
            tenant_id=tenant,
            artifact_class=artifact_class,
            name=name,
        )

    def get(self, *, content_address: str) -> bytes:
        return self.inner.get(content_address=content_address)

    def exists(self, *, content_address: str) -> bool:
        return self.inner.exists(content_address=content_address)

    def resolve_uri(self, *, uri: str) -> str:
        return self.inner.resolve_uri(uri=uri)


@dataclass
class _RecordingDereference:
    """``govern_dereference`` in its §1.2 shape, answering as told and
    remembering every ask."""

    answer: DereferencedEvidence | RefusalEnvelope
    asked: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, authorized: object, **kwargs: Any) -> DereferencedEvidence | RefusalEnvelope:
        self.asked.append({"authorized": authorized, **kwargs})
        return self.answer


@dataclass
class _RecordingAuthorizer:
    """Delegates to a real authorizer and remembers what it was asked."""

    inner: Any
    asked: list[dict[str, Any]] = field(default_factory=list)

    def authorize(
        self, *, grant: TokenGrant, tenant: str, action_id: str, resource: str
    ) -> AuthzDecision:
        self.asked.append({"tenant": tenant, "action_id": action_id, "resource": resource})
        return cast(
            AuthzDecision,
            self.inner.authorize(
                grant=grant, tenant=tenant, action_id=action_id, resource=resource
            ),
        )


@dataclass
class _World:
    server: FastMCP
    store: _RecordingStore
    authorizer: _RecordingAuthorizer
    audit_log: Any


def _world(tmp_path: pathlib.Path, *, authorizer: Any = None) -> _World:
    source, recorder = _entitlement_world(tmp_path)
    store = _RecordingStore(inner=FileArtifactStore(root=tmp_path / "artifacts"))
    recording = _RecordingAuthorizer(
        inner=authorizer if authorizer is not None else authorizer_granting()
    )
    audit_log = ControlPlaneRegistry().audit_log
    server = build_artifact_server(
        server_name="authorized-artifact",
        store=store,  # type: ignore[arg-type]  # the §1.2 write shape, ahead of the join
        token_verifier=SourceBackedTokenVerifier(
            source=StaticTokenSource(grants={"tok": _grant(TENANT)})
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://artifact.invalid/mcp"),
            required_scopes=[SCOPE],
        ),
        authorizer=recording,
        entitlement_source=source,
        refusal_recorder=recorder,
        audit_log=audit_log,
    )
    return _World(server=server, store=store, authorizer=recording, audit_log=audit_log)


def _put(world: _World, *, artifact_class: str = "c", name: str = "n", payload: object = None) -> Any:
    canonical = canonical_bytes({} if payload is None else payload)
    return anyio.run(
        world.server.call_tool,
        PUT_ARTIFACT_TOOL,
        {
            "artifact_class": artifact_class,
            "name": name,
            "canonical_b64": base64.b64encode(canonical).decode("ascii"),
        },
    )


def _envelope() -> RefusalEnvelope:
    return envelope_for(
        SubjectUnavailableRefusal(
            cause="nonexistent",
            detail="the requested evidence is not available to this principal",
            error_code=ERROR_EVIDENCE_ABSENT,
        ),
        request=RequestIdentity(
            product_id="ccf.evidence-dereference",
            product_version=None,
            parameters={"reference": ADDRESS},
            temporal_boundary=None,
        ),
    )


def _evidence(payload: bytes) -> DereferencedEvidence:
    return DereferencedEvidence(
        content_address=ADDRESS,
        # The contract tests measure the body's call, not the record; a
        # placeholder stands where the real path carries a replay record.
        record=cast(DecisionReplayRecord, object()),
        payload=payload,
    )


# --- put_artifact: the tenant_id argument is gone; the store takes the capability ---


def test_put_artifact_takes_no_tenant_argument(tmp_path: pathlib.Path) -> None:
    """``tenant_id`` is deleted from the input schema (§1.2, §1.3). The tenant
    is ``authorized.tenant`` and there is no second source."""
    world = _world(tmp_path)
    tools = {tool.name: tool for tool in anyio.run(world.server.list_tools)}
    schema = tools[PUT_ARTIFACT_TOOL].inputSchema
    assert set(schema["required"]) == {"artifact_class", "name", "canonical_b64"}
    assert "tenant_id" not in schema["properties"]
    assert "authorized" not in schema["properties"]


def test_put_artifact_hands_the_store_a_write_capability_for_class_slash_name(
    tmp_path: pathlib.Path,
) -> None:
    """The positive control: ``store.put(authorized, artifact)`` receives a
    genuine ``Authorized[ArtifactWrite]`` for ``"<class>/<name>"`` under the
    grant's tenant, and the class and name reach the store through the
    capability alone."""
    world = _world(tmp_path)
    reset = _as_grant(_grant(TENANT))
    try:
        _, structured = _put(world, artifact_class="c", name="n")
    finally:
        auth_context_var.reset(reset)
    ((authorized, artifact),) = world.store.puts
    verify(authorized, kind=ArtifactWrite, resource="c/n")
    assert getattr(authorized, "tenant") == TENANT
    assert getattr(authorized, "principal") == PRINCIPAL
    assert artifact == {}
    assert ArtifactRef.model_validate(structured).tenant_id == TENANT
    assert world.authorizer.asked == [
        {"tenant": TENANT, "action_id": ACTION_ARTIFACT_WRITE, "resource": "c/n"}
    ]


def test_put_artifact_under_a_grant_spanning_two_tenants_is_ambiguous(
    tmp_path: pathlib.Path,
) -> None:
    """No tenant on the wire and two in the grant: refused, the store untouched
    (§1.3 — the gate does not pick)."""
    world = _world(tmp_path)
    reset = _as_grant(_grant(TENANT, FOREIGN))
    try:
        refused = _refusal(lambda: _put(world))
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, AmbiguousTenantRefused)
    assert world.store.puts == []
    assert world.authorizer.asked == []


def test_put_artifact_is_refused_when_the_mapping_grants_reads_only(
    tmp_path: pathlib.Path,
) -> None:
    """A read-only scope reaches the write tool: the authorizer says no, nothing
    is minted, the store is never called."""
    world = _world(tmp_path, authorizer=authorizer_granting(actions=(ACTION_ARTIFACT_READ,)))
    reset = _as_grant(_grant(TENANT))
    try:
        refused = _refusal(lambda: _put(world))
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, ActionUnauthorizedRefused)
    assert world.store.puts == []


def test_put_artifact_still_refuses_a_non_canonical_payload_before_the_store(
    tmp_path: pathlib.Path,
) -> None:
    world = _world(tmp_path)
    reset = _as_grant(_grant(TENANT))
    try:
        refused = _refusal(
            lambda: anyio.run(
                world.server.call_tool,
                PUT_ARTIFACT_TOOL,
                {
                    "artifact_class": "c",
                    "name": "n",
                    "canonical_b64": base64.b64encode(b'{"b": 1, "a": 2}').decode("ascii"),
                },
            )
        )
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, NonCanonicalPayload)
    assert world.store.puts == []


def test_the_write_capability_is_not_a_wand_for_another_name(tmp_path: pathlib.Path) -> None:
    """§9's wrong-resource control at this surface: the capability minted for
    ``c/n`` dies at ``verify`` for ``c/other`` — the store's own line."""
    world = _world(tmp_path)
    reset = _as_grant(_grant(TENANT))
    try:
        _put(world, artifact_class="c", name="n")
    finally:
        auth_context_var.reset(reset)
    ((authorized, _),) = world.store.puts
    with pytest.raises(CapabilityBypassError, match="resource"):
        verify(authorized, kind=ArtifactWrite, resource="c/other")
    with pytest.raises(CapabilityBypassError, match="kind"):
        verify(authorized, kind=ArtifactRead, resource="c/n")


# --- blob and presence: through the governed dereference, with a read capability ---


def test_the_blob_read_goes_through_the_governed_dereference(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """There is no untenanted read of artifact bytes (§2 P5). The body hands
    ``govern_dereference`` a genuine ``Authorized[ArtifactRead]`` for the
    address, a bytes ask, this surface's identity and the blob URI — and
    returns exactly the payload the dereference delivered."""
    dereference = _RecordingDereference(answer=_evidence(b'{"x": 1}'))
    monkeypatch.setattr(module, "govern_dereference", dereference)
    world = _world(tmp_path)
    reset = _as_grant(_grant(TENANT))
    try:
        contents = anyio.run(world.server.read_resource, artifact_blob_uri(content_address=ADDRESS))
    finally:
        auth_context_var.reset(reset)
    (served,) = contents
    assert served.content == b'{"x": 1}'
    (asked,) = dereference.asked
    verify(asked["authorized"], kind=ArtifactRead, resource=ADDRESS)
    assert getattr(asked["authorized"], "tenant") == TENANT
    assert asked["reference"] == DereferenceRequest(reference=ADDRESS, by_uri=False, wants_bytes=True)
    assert asked["store"] is world.store
    assert asked["audit_log"] is world.audit_log
    assert asked["surface"] == SURFACE_MCP_RESOURCE
    assert asked["address"] == artifact_blob_uri(content_address=ADDRESS)
    assert world.authorizer.asked == [
        {"tenant": TENANT, "action_id": ACTION_ARTIFACT_READ, "resource": ADDRESS}
    ]


def test_the_presence_read_goes_through_the_governed_dereference_too(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dereference = _RecordingDereference(answer=_evidence(b"{}"))
    monkeypatch.setattr(module, "govern_dereference", dereference)
    world = _world(tmp_path)
    reset = _as_grant(_grant(TENANT))
    try:
        contents = anyio.run(world.server.read_resource, artifact_meta_uri(content_address=ADDRESS))
    finally:
        auth_context_var.reset(reset)
    (served,) = contents
    assert ArtifactPresence.model_validate_json(str(served.content)).found is True
    (asked,) = dereference.asked
    verify(asked["authorized"], kind=ArtifactRead, resource=ADDRESS)
    assert asked["address"] == artifact_meta_uri(content_address=ADDRESS)


def test_a_refused_dereference_crosses_as_the_envelopes_canonical_bytes(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A governed *no* is a response, not a transport error (``D-IMPL-256``):
    the blob carries the shell's canonical bytes — which cannot hash to the
    address asked for, so a verifying client cannot mistake them for the
    artifact — and the presence resource carries the same shell as text."""
    envelope = _envelope()
    monkeypatch.setattr(module, "govern_dereference", _RecordingDereference(answer=envelope))
    world = _world(tmp_path)
    reset = _as_grant(_grant(TENANT))
    try:
        (blob,) = anyio.run(world.server.read_resource, artifact_blob_uri(content_address=ADDRESS))
        (meta,) = anyio.run(world.server.read_resource, artifact_meta_uri(content_address=ADDRESS))
    finally:
        auth_context_var.reset(reset)
    assert blob.content == canonical_bytes(envelope)
    assert content_hash(json.loads(canonical_bytes(envelope))) != ADDRESS
    assert RefusalEnvelope.model_validate_json(str(meta.content)) == envelope


def test_a_multi_tenant_grant_cannot_read_a_blob_it_names_no_tenant_for(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dereference = _RecordingDereference(answer=_evidence(b"{}"))
    monkeypatch.setattr(module, "govern_dereference", dereference)
    world = _world(tmp_path)
    reset = _as_grant(_grant(TENANT, FOREIGN))
    try:
        refused = _refusal(
            lambda: anyio.run(world.server.read_resource, artifact_blob_uri(content_address=ADDRESS))
        )
    finally:
        auth_context_var.reset(reset)
    assert isinstance(refused, AmbiguousTenantRefused)
    assert dereference.asked == []


# --- the naming resource: tenant-decided by its segment, class/name as resource ---


def test_the_naming_resource_decides_its_tenant_segment_and_names_class_slash_name(
    tmp_path: pathlib.Path,
) -> None:
    world = _world(tmp_path)
    own = NAME_URI_TEMPLATE.format(
        tenant=TENANT, artifact_class="c", name="n", artifact_version="1.0.0"
    )
    foreign = NAME_URI_TEMPLATE.format(
        tenant=FOREIGN, artifact_class="c", name="n", artifact_version="1.0.0"
    )
    reset = _as_grant(_grant(TENANT))
    try:
        (served,) = anyio.run(world.server.read_resource, own)
        refused = _refusal(lambda: anyio.run(world.server.read_resource, foreign))
    finally:
        auth_context_var.reset(reset)
    assert ArtifactResolution.model_validate_json(str(served.content)).found is False
    assert isinstance(refused, CrossTenantRefused)
    assert world.authorizer.asked == [
        {"tenant": TENANT, "action_id": ACTION_ARTIFACT_READ, "resource": "c/n"}
    ]
    assert own.startswith(ARTIFACT_URI_SCHEME + "://")


# --- the untenanted reading is gone -------------------------------------------


def test_no_surface_on_the_artifact_server_is_untenanted(tmp_path: pathlib.Path) -> None:
    """``untenanted()`` is deleted: every capability names its tenant. The two
    hash-addressed resources select the grant's sole tenant; the other two
    read the URI's segment."""
    assert not hasattr(TenantGuardedServer, "untenanted")
    assert "untenanted_surfaces" not in tenancy.__all__
    world = _world(tmp_path)
    # The ledger is per FastMCP; reach it through the module's weak map the
    # same way `unguarded_surfaces` does, since the builder returns the server.
    ledger = tenancy._LEDGERS[world.server]
    assert set(ledger) == {
        BLOB_URI_TEMPLATE, META_URI_TEMPLATE, NAME_URI_TEMPLATE, PUT_ARTIFACT_TOOL
    }
    assert ledger[BLOB_URI_TEMPLATE].subject.grant is True
    assert ledger[META_URI_TEMPLATE].subject.grant is True
    assert ledger[NAME_URI_TEMPLATE].subject.argument == "tenant"
    assert ledger[PUT_ARTIFACT_TOOL].subject.grant is True
    assert ledger[PUT_ARTIFACT_TOOL].action == ACTION_ARTIFACT_WRITE
    assert ledger[PUT_ARTIFACT_TOOL].resource.template == "{artifact_class}/{name}"
    for uri in (BLOB_URI_TEMPLATE, META_URI_TEMPLATE, NAME_URI_TEMPLATE):
        assert ledger[uri].action == ACTION_ARTIFACT_READ
        assert ledger[uri].mutating is False


# --- the real path, ahead of the join -----------------------------------------


def _real_world(tmp_path: pathlib.Path) -> tuple[FastMCP, FileArtifactStore]:
    source, recorder = _entitlement_world(tmp_path)
    store = FileArtifactStore(root=tmp_path / "artifacts")
    server = build_artifact_server(
        server_name="authorized-artifact-real",
        store=store,
        token_verifier=SourceBackedTokenVerifier(
            source=StaticTokenSource(grants={"tok": _grant(TENANT)})
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://artifact.invalid/mcp"),
            required_scopes=[SCOPE],
        ),
        authorizer=authorizer_granting(),
        entitlement_source=source,
        refusal_recorder=recorder,
        audit_log=ControlPlaneRegistry().audit_log,
    )
    return server, store


@pytest.mark.xfail(strict=True, reason=JOIN)
def test_put_artifact_files_under_the_capabilitys_tenant_through_the_real_store(
    tmp_path: pathlib.Path,
) -> None:
    """Post-join: the shipped store files ``{}`` as ``c/n`` under the grant's
    tenant, resolvable by the versioned URI the reference carries."""
    server, store = _real_world(tmp_path)
    reset = _as_grant(_grant(TENANT))
    try:
        _, structured = anyio.run(
            server.call_tool,
            PUT_ARTIFACT_TOOL,
            {
                "artifact_class": "c",
                "name": "n",
                "canonical_b64": base64.b64encode(canonical_bytes({})).decode("ascii"),
            },
        )
    finally:
        auth_context_var.reset(reset)
    ref = ArtifactRef.model_validate(structured)
    assert ref.tenant_id == TENANT
    assert store.resolve_uri(uri=ref.uri) == ref.content_address == content_hash({})


@pytest.mark.xfail(strict=True, reason=JOIN)
def test_the_real_dereference_answers_a_non_record_artifact_with_a_shell(
    tmp_path: pathlib.Path,
) -> None:
    """The §2 P5 consequence, stated as evidence rather than hidden: the
    governed dereference resolves its target as a Decision Replay record, so a
    stored artifact of any other class answers the ``nonexistent`` shell
    through the blob resource. The HTTP artifact GET has had this property
    since ``D-IMPL-345``; the MCP blob now has it too."""
    server, store = _real_world(tmp_path)
    ref = store.put(tenant_id=TENANT, artifact_class="c", name="n", artifact={"not": "a record"})
    reset = _as_grant(_grant(TENANT))
    try:
        (blob,) = anyio.run(server.read_resource, artifact_blob_uri(content_address=ref.content_address))
    finally:
        auth_context_var.reset(reset)
    shell = RefusalEnvelope.model_validate_json(bytes(cast(bytes, blob.content)).decode("utf-8"))
    assert shell.request.product_id == "ccf.evidence-dereference"
