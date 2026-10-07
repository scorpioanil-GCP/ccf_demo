"""C8 — the artifact server judges "governed" over the CALLER'S OWN TENANT'S filings (`D-IMPL-376` ruling (6)).

The deadline-rows close panel's C8 (codex, B5): the split behind the blob and
presence resources and the SEC-009 names resource
(:func:`ccf_runtime.mcp.artifact_server.build_artifact_server`) computed
``governed`` over EVERY tenant's filings of a content address, before the
own-tenant filter. Content addressing files identical bytes once, so another
tenant's governed filing of the same bytes changed the owner's reads:

* tenant A's own client-lane blob, presence and names reads of bytes X became
  the ``subject-unavailable`` shell once tenant B filed X under a class the
  substrate declares under ``ReplayMint``;
* A's answers told it whether ANY other tenant held bytes A can compute — with
  its own filing (served bytes or the shell), and on the names resource from
  the address alone (``[]`` or the shell): a cross-tenant existence oracle;
* A's erasure door over the MCP-backed reference store refused A's own address
  ``class-unverifiable``, because the names read it verifies through answered
  the shell.

The contract held here: a tenant's answers about an address depend on its own
tenant's filings only. Same-tenant governance is not relaxed — a governed
filing by the caller's own tenant still sends every caller of that tenant
through the governed dereference, which
``tests/mcp/test_artifact_server_authorized.py::test_a_governed_class_stays_governed_through_the_split``
and
``tests/mcp/test_sec009_mcp_names_at.py::test_the_names_resource_requires_the_entitlement_a_governed_read_requires``
keep measuring.

Tenant, principal, class, scope and token names are test deployment
vocabulary, meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any

import anyio
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

import ccf.artifacts.mcp_store as mcp_store_module
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.mcp_store import McpArtifactStore
from ccf.artifacts.protocol import ArtifactName, DerivedWrite, WriteKinds
from ccf.authz.capability import ArtifactWrite, ReplayMint
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.audit import AuthzDecisionAuditEvent
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf_runtime.mcp.artifact_server import (
    ArtifactPresence,
    artifact_blob_uri,
    artifact_meta_uri,
    artifact_names_uri,
    build_artifact_server,
)
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource, TokenGrant
from tests.composition import declared_erasure_trust, no_erasures
from tests.controlplane.capabilities import capability
from tests.erasure import harness as h
from tests.http_api.composition_authority import composition_replay_mint, deployment_store
from tests.mcp import test_sec009_mcp_names_at as names_world
from tests.mcp.guarded_servers import (
    FOREIGN,
    PRINCIPAL,
    REPLAY_RECORD_CLASS,
    SCOPE,
    TENANT,
    _entitlement_world,
    authorizer_granting,
)
from tests.mcp.test_artifact_server_authorized import _as_grant

#: The bytes both tenants file. Any document serves; this one is the panel probe's.
DOCUMENT = {"seeds": ["s"]}

#: A client-lane class: one the substrate does not declare governed.
CLIENT_CLASS = "c"

#: The three worlds an owner's answers must not be able to tell apart.
WORLDS = ("no-other-filing", "other-tenant-client-lane", "other-tenant-governed")

SURFACES = ("blob", "meta", "names")


@dataclass
class _World:
    server: FastMCP
    store: FileArtifactStore
    audit_log: Any


def _world(tmp_path: pathlib.Path) -> _World:
    """The shipped server over the shipped file store, one governed class declared."""
    source, recorder = _entitlement_world(tmp_path)
    store = deployment_store(tmp_path / "artifacts", REPLAY_RECORD_CLASS)
    audit_log = ControlPlaneRegistry().audit_log
    server = build_artifact_server(
        server_name="c8-governed-per-tenant",
        store=store,
        token_verifier=SourceBackedTokenVerifier(
            source=StaticTokenSource(grants={"tok": _grant()})
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://artifact.invalid/mcp"),
            required_scopes=[SCOPE],
        ),
        authorizer=authorizer_granting(),
        entitlement_source=source,
        refusal_recorder=recorder,
        audit_log=audit_log,
        erasure_trust=declared_erasure_trust(),
        erasure_index=no_erasures(),
        control_plane=ControlPlaneRegistry(),
    )
    return _World(server=server, store=store, audit_log=audit_log)


def _grant() -> TokenGrant:
    return TokenGrant(client_id=PRINCIPAL, scopes=(SCOPE,), tenants=frozenset({TENANT}))


def _owner_files(world: _World) -> str:
    """Tenant A files the document on the client lane; returns its content address."""
    ref = world.store.put(
        capability(ArtifactWrite, tenant=TENANT, resource=f"{CLIENT_CLASS}/mine"), DOCUMENT
    )
    return ref.content_address


def _other_tenant_files(world: _World, kind: str) -> None:
    """Tenant B files the SAME bytes — on its client lane, or under the governed class."""
    if kind == "no-other-filing":
        return
    if kind == "other-tenant-client-lane":
        world.store.put(
            capability(ArtifactWrite, tenant=FOREIGN, resource=f"{CLIENT_CLASS}/theirs"), DOCUMENT
        )
        return
    assert kind == "other-tenant-governed", kind
    world.store.put(
        composition_replay_mint(
            ControlPlaneRegistry(), tenant=FOREIGN, artifact_class=REPLAY_RECORD_CLASS
        ),
        DerivedWrite(artifact_class=REPLAY_RECORD_CLASS, name="theirs", artifact=DOCUMENT),
    )


def _uri(surface: str, address: str) -> str:
    render = {
        "blob": artifact_blob_uri,
        "meta": artifact_meta_uri,
        "names": artifact_names_uri,
    }[surface]
    return render(content_address=address)


def _read_as_owner(world: _World, surface: str, address: str) -> bytes:
    """Tenant A's answer on one hash-addressed surface, as the exact bytes that crossed."""
    reset = _as_grant(_grant())
    try:
        (answer,) = list(anyio.run(world.server.read_resource, _uri(surface, address)))
    finally:
        auth_context_var.reset(reset)
    content = answer.content
    return content if isinstance(content, bytes) else content.encode("utf-8")


def _answers(world: _World, address: str) -> dict[str, bytes]:
    return {surface: _read_as_owner(world, surface, address) for surface in SURFACES}


def test_another_tenants_governed_filing_does_not_change_the_owners_reads(
    tmp_path: pathlib.Path,
) -> None:
    """(a) Tenant A's blob, presence and names answers for its own client-lane
    filing are the same bytes before and after tenant B files those bytes under
    a ``ReplayMint`` class — and they are the client lane's answers: the exact
    stored bytes, ``found: true``, A's own name, and one R-5 ``authz_decision``
    event naming A's class for the blob read."""
    world = _world(tmp_path)
    address = _owner_files(world)
    before = _answers(world, address)

    _other_tenant_files(world, "other-tenant-governed")
    assert world.store.names_at(content_address=address) != (), "B's filing is in the index"
    assert any(
        named.tenant_id == FOREIGN and named.artifact_class == REPLAY_RECORD_CLASS
        for named in world.store.names_at(content_address=address)
    ), "the same address is now filed by B under the governed class"

    events_before = len(world.audit_log.events())
    after = _answers(world, address)

    for surface in SURFACES:
        assert after[surface] == before[surface], (
            f"{surface}: tenant A's answer changed when tenant B filed the same bytes"
            f" governed: before={before[surface][:120]!r} after={after[surface][:120]!r}"
        )
    # The mechanism, by name: the client lane served A's own filing.
    assert after["blob"] == canonical_bytes(DOCUMENT)
    assert content_hash(json.loads(after["blob"])) == address
    assert ArtifactPresence.model_validate_json(after["meta"]).found is True
    assert [ArtifactName.model_validate(item) for item in json.loads(after["names"])] == [
        ArtifactName(
            tenant_id=TENANT, artifact_class=CLIENT_CLASS, name="mine", artifact_version=address
        )
    ]
    trail = [
        event
        for event in world.audit_log.events()[events_before:]
        if isinstance(event, AuthzDecisionAuditEvent)
    ]
    assert [(event.key, event.artifact_class, event.actor) for event in trail] == [
        (address, CLIENT_CLASS, PRINCIPAL),
        (address, CLIENT_CLASS, PRINCIPAL),
    ], "the blob and presence reads each left the client lane's R-5 trail, under A's class"


@pytest.mark.parametrize("owner_filed", [True, False], ids=["owner-filed", "owner-never-filed"])
def test_the_owners_answers_do_not_depend_on_any_other_tenants_filing(
    tmp_path: pathlib.Path, owner_filed: bool
) -> None:
    """(b) The existence oracle, closed: for one address, tenant A's blob,
    presence and names answers are byte-identical whether no other tenant filed
    the bytes, another tenant filed them on its client lane, or another tenant
    filed them under the governed class — with A's own filing, and without it
    (where the names resource used to answer ``[]`` for nothing and the
    governed refusal's shell for another tenant's governed filing)."""
    address = content_hash(DOCUMENT)
    answers: dict[str, dict[str, bytes]] = {}
    for kind in WORLDS:
        (tmp_path / kind).mkdir()
        world = _world(tmp_path / kind)
        if owner_filed:
            assert _owner_files(world) == address
        _other_tenant_files(world, kind)
        answers[kind] = _answers(world, address)

    for surface in SURFACES:
        by_world = {kind: answers[kind][surface] for kind in WORLDS}
        assert len(set(by_world.values())) == 1, (
            f"{surface}: tenant A's answer depends on another tenant's filing: "
            + "; ".join(f"{kind}={value[:100]!r}" for kind, value in by_world.items())
        )
    if not owner_filed:
        # Without an own filing the names answer is the caller's own names: none.
        assert json.loads(answers["other-tenant-governed"]["names"]) == []


def test_the_owners_erasure_over_the_mcp_backed_store_is_not_refused_by_another_tenants_governed_filing(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(c) The SEC-009 consequence C8 named: with tenant B holding the owner's
    bytes under a governed class, the owner's erasure door over the MCP-backed
    reference store verifies the owner's own address and admits the request
    (it suspends on the approval gate), rather than refusing it
    ``class-unverifiable`` — the same outcome the in-process door gives."""
    plane = h.compose(tmp_path)
    base = h.write_kinds()
    governed_kinds = WriteKinds(
        {
            **{declared: base.for_class(declared) for declared in base.declared_classes},
            REPLAY_RECORD_CLASS: (ReplayMint,),
        }
    )
    # The same substrate (one root, one naming index), declaring one governed class.
    substrate = FileArtifactStore(root=plane.store.root, write_kinds=governed_kinds)
    theirs = substrate.put(
        composition_replay_mint(
            ControlPlaneRegistry(), tenant=names_world.FOREIGN, artifact_class=REPLAY_RECORD_CLASS
        ),
        DerivedWrite(
            artifact_class=REPLAY_RECORD_CLASS,
            name="theirs",
            artifact={"customer": {"id": h.SUBJECT_ID}, "note": "kyc"},
        ),
    )
    assert theirs.content_address == plane.document.content_address  # identical bytes, two tenants

    server = names_world._server(tmp_path, substrate)
    session = names_world._InProcessSession(server)

    async def run_with_session(*, url: str, operation: Any, http_client_factory: Any) -> Any:
        return await operation(session)

    monkeypatch.setattr(mcp_store_module, "run_with_session", run_with_session)
    client = McpArtifactStore(url="http://artifact.invalid/mcp", bridge=names_world._Run(), write_kinds=h.write_kinds())  # type: ignore[arg-type]
    door = h.door(plane, store=client)
    request = h.request(plane)
    suspended = h.run(
        door.request(
            h.execute_cap(),
            definition_version=plane.definition_version,
            request=request,
            erase=h.erase_cap(request),
        )
    )
    assert getattr(suspended, "event_key", None), suspended
    names = client.names_at(content_address=plane.document.content_address)
    assert {(n.tenant_id, n.artifact_class) for n in names} == {(h.TENANT, h.DOC_CLASS)}
