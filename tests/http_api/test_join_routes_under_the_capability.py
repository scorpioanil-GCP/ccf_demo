"""The HTTP doors call the §1.2 handles with the capability the gate minted (D-IMPL-353; the join).

Measured over a MINIMAL bundle — one Control Plane, one declaring store, a
resolver that serves nothing — rather than the shared ``Fabric``: the fabric
ingests events at construction, and at the join base that path reaches
``ccf.controlplane.invalidation`` (J-SRC's, red until its composition root
mints for it), so a proof that waited for the fabric would wait for another
lane. Nothing here depends on ingestion. Every claim below is drafted from
what would fail:

=====================================  =====================================
Claim                                  What would fail here
=====================================  =====================================
the artifact write is decided on       a scope mapping could grant a name and
``"<class>/<name>"``                   not a class, or the door could decide
                                       on one string and the store file under
                                       another
a body that cannot spell the resource  a caller could omit the field the gate
is a deny at the gate                  decides on and reach the handler
the registry key IS the capability's   a handler could register under a key
resource, the actor its principal      other than the one authorized, or
                                       audit the write to nobody
the catalog route decides on the       a scope could register an entry under
entry's own key                        another tenant's key
the evidence routes dereference under  a read could reach the store outside
the capability                         the governed step
=====================================  =====================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.agents.definitions import AGENT_DEFINITION, PROMPT_ARTIFACT
from ccf.authz.decision import AuthzDecision
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.projection.plan import Perspective
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalog, skill_catalog_key
from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource
from ccf_runtime.authz.refusals import (
    ACTION_AGENT_DECLARE,
    ACTION_ARTIFACT_WRITE,
    ACTION_CONFIG_REGISTER,
    ACTION_SKILL_CATALOG_REGISTER,
)
from ccf_runtime.http_api.app import create_app
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import ERROR_REQUEST_UNAUTHORIZED, ERROR_TENANT_UNAUTHORIZED
from ccf_runtime.http_api.routes.artifact import ARTIFACT_WRITE_RESOURCE
from ccf_runtime.http_api.routes.skill import CATALOG_REGISTER_RESOURCE
from ccf_runtime.mcp.auth import TokenGrant
from ccf_runtime.mcp.egress import ProductNotServable
from http_api.composition_authority import (
    deployment_store,
    refusal_recorder,
    register_typed_at_composition,
)
from http_api.conftest import _load
from http_api.gate_fixtures import SCOPE_EVERYTHING, authority, probe

#: The fixture agent's tenant, so the banking artifacts register under keys
#: the credential's tenant owns. Test vocabulary (CINV-01).
TENANT = "acme-bank"
CLIENT = "join-caller"
TOKEN = "join-token"
ROLE = "join-role"
REPLAY_RECORD_CLASS = "ccf.decision-replay-record"
INSTANT = datetime(2026, 9, 24, tzinfo=UTC)


@dataclass
class _Recording:
    """The real authorizer, remembering every resource it was asked about."""

    inner: Any
    asked: list[tuple[str, str]] = field(default_factory=list)

    def authorize(self, *, grant: TokenGrant, tenant: str, action_id: str, resource: str) -> AuthzDecision:
        self.asked.append((action_id, resource))
        decision: AuthzDecision = self.inner.authorize(
            grant=grant, tenant=tenant, action_id=action_id, resource=resource
        )
        return decision


@dataclass
class _World:
    app: Any
    registry: ControlPlaneRegistry
    store: Any
    authorizer: _Recording

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {TOKEN}"}


def _resolver(**kwargs: Any) -> Any:
    raise ProductNotServable("this bundle serves no product")


def _world(tmp_path: Path) -> _World:
    registry = ControlPlaneRegistry()
    store = deployment_store(tmp_path / "artifacts", REPLAY_RECORD_CLASS)
    entitlements = ControlPlaneRegistry()
    register_typed_at_composition(
        entitlements,
        product_entitlement_key(tenant_id=TENANT),
        ProductEntitlementPolicy(
            tenant_id=TENANT,
            policy_version="1.0.0",
            principals={
                CLIENT: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({"join.product"}),
                    permitted_roles=frozenset({ROLE}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    source = ControlPlaneProductEntitlementSource(control_plane=entitlements, clock=lambda: INSTANT)
    seams = authority(
        tenant=TENANT,
        key="join/mapping",
        grants={TOKEN: (CLIENT, (SCOPE_EVERYTHING,))},
        product_entitlement=source,
        perspective_resolver=lambda *, grant, tenant, requested_role: Perspective(
            principal_id=grant.client_id, role=ROLE
        ),
        refusal_recorder=refusal_recorder(
            registry,
            store=store,
            tenant=TENANT,
            replay_record_class=REPLAY_RECORD_CLASS,
            disclosure_level_for=source.disclosure_level_for,
        ),
        clock_at=INSTANT,
    )
    recording = _Recording(inner=seams["authorizer"])
    seams["authorizer"] = recording
    app = create_app(
        ApiDependencies(
            control_plane=registry,
            artifact_store=store,
            product_resolver=_resolver,
            skill_catalog=SkillCatalog(registry),
        ),
        **seams,
    )
    return _World(app=app, registry=registry, store=store, authorizer=recording)


@pytest.fixture
def world(tmp_path: Path) -> _World:
    return _world(tmp_path)


# --- artifact PUT: decided on "<class>/<name>", filed under the capability -------


def test_an_artifact_write_is_decided_on_class_slash_name_and_filed_under_exactly_it(
    world: _World,
) -> None:
    filed = probe(
        world.app,
        "POST",
        "/artifact",
        headers=world.headers(),
        json={"artifact_class": "join-blob", "name": "one", "artifact": {"k": 1}},
    )
    assert filed.status_code == 200, filed.text
    assert ARTIFACT_WRITE_RESOURCE.format(artifact_class="join-blob", name="one") == "join-blob/one"
    assert (ACTION_ARTIFACT_WRITE, "join-blob/one") in world.authorizer.asked
    ref = filed.json()
    assert ref["tenant_id"] == TENANT
    assert ref["uri"].startswith(f"ccf-artifact://{TENANT}/join-blob/one@")
    (named,) = world.store.names_at(content_address=ref["content_address"])
    assert (named.tenant_id, named.artifact_class, named.name) == (TENANT, "join-blob", "one")


@pytest.mark.parametrize(
    "body",
    [
        {"artifact_class": "join-blob", "artifact": {}},
        {"artifact_class": "join-blob", "name": "", "artifact": {}},
        {"name": "one", "artifact": {}},
    ],
    ids=["no-name", "empty-name", "no-class"],
)
def test_a_body_that_cannot_spell_the_resource_is_denied_at_the_gate(
    world: _World, body: dict[str, Any]
) -> None:
    before = len(world.authorizer.asked)
    refused = probe(world.app, "POST", "/artifact", headers=world.headers(), json=body)
    assert refused.status_code == 403
    assert refused.json()["detail"]["error_code"] == ERROR_REQUEST_UNAUTHORIZED
    # A deny, never a skip: the authorizer was not even asked, and nothing
    # was filed.
    assert world.authorizer.asked[before:] == []
    assert world.store.names_at(content_address=content_hash({})) == ()


# --- the registration doors: the key IS the capability's resource -----------------


def test_an_agent_declaration_registers_under_the_authorized_key_as_the_principal(
    world: _World,
) -> None:
    definition = _load("skills/grants.yaml")["agents"]["auto"]
    key = f"{TENANT}/agents/{definition['name']}"
    declared = probe(
        world.app,
        "POST",
        "/agent/declarations",
        headers=world.headers(),
        json={"key": key, "definition": definition},
    )
    assert declared.status_code == 200, declared.text
    assert declared.json()["key"] == key
    assert (ACTION_AGENT_DECLARE, key) in world.authorizer.asked
    assert world.registry.versions(key) == (declared.json()["version"],)
    (event,) = [e for e in world.registry.audit_events() if e.action == "register_versioned"]
    assert event.key == key
    assert event.actor == CLIENT


def test_a_config_registration_registers_under_the_authorized_key(world: _World) -> None:
    fixture = _load("prompts/covenant_summary.yaml")
    key = fixture["keys"]["prompt_artifact"]
    assert key.startswith(f"{TENANT}/")
    registered = probe(
        world.app,
        "POST",
        "/config/registrations",
        headers=world.headers(),
        json={
            "key": key,
            "class_id": PROMPT_ARTIFACT.class_id,
            "artifact": fixture["prompt_artifact"],
        },
    )
    assert registered.status_code == 200, registered.text
    assert registered.json()["key"] == key
    assert (ACTION_CONFIG_REGISTER, key) in world.authorizer.asked
    assert world.registry.versions(key) == (registered.json()["version"],)


def test_a_catalog_registration_is_decided_on_the_entrys_own_key(world: _World) -> None:
    entry = _load("skills/covenant_metrics_tool.yaml")["entry"]
    parsed = parse_artifact(entry, SKILL_CATALOG_ENTRY)
    key = skill_catalog_key(parsed)  # type: ignore[arg-type]
    assert key == CATALOG_REGISTER_RESOURCE.format(tenant=entry["tenant"], name=entry["name"])
    registered = probe(world.app, "POST", "/skill/catalog", headers=world.headers(), json=entry)
    assert registered.status_code == 200, registered.text
    assert (ACTION_SKILL_CATALOG_REGISTER, key) in world.authorizer.asked
    assert world.registry.versions(key) == (registered.json()["version"],)


def test_a_catalog_entry_naming_another_tenant_is_refused_and_nothing_registers(
    world: _World,
) -> None:
    entry = dict(_load("skills/covenant_metrics_tool.yaml")["entry"])
    entry["tenant"] = "some-other-bank"
    before = sorted(world.registry.keys_of_class(SKILL_CATALOG_ENTRY.class_id))
    refused = probe(world.app, "POST", "/skill/catalog", headers=world.headers(), json=entry)
    assert refused.status_code == 403
    assert refused.json()["detail"]["error_code"] == ERROR_TENANT_UNAUTHORIZED
    assert sorted(world.registry.keys_of_class(SKILL_CATALOG_ENTRY.class_id)) == before


# --- the evidence routes dereference under the capability ------------------------


def test_the_evidence_routes_answer_a_recorded_shell_under_the_capability(world: _World) -> None:
    """Both doors reach `govern_dereference(authorized, ...)`: a nonexistent
    address is a recorded, disclosed shell whose replay reference resolves in
    the store the recorder writes through."""
    from ccf.products.refusal import REFUSAL_KINDS, SubjectUnavailableRefusal
    from ccf_runtime.http_api.refusal_status import STATUS_BY_KIND

    status = STATUS_BY_KIND[REFUSAL_KINDS[SubjectUnavailableRefusal]]
    nowhere = "e" * 64
    artifact = probe(world.app, "GET", f"/artifact/{nowhere}", headers=world.headers())
    replay = probe(world.app, "GET", "/replay/decisions", params={"content_address": nowhere}, headers=world.headers())
    for response in (artifact, replay):
        assert response.status_code == status, response.text
        reference = response.json()["refusal"]["replay_reference"]
        assert world.store.exists(content_address=world.store.resolve_uri(uri=reference))


# --- create_app's boot check over WriteKinds (D-IMPL-353 §3), fabric-free --------
#
# The same three controls live in ``test_capability_gate.py`` over the shared
# fabric; they are repeated here over the minimal bundle so the boot check is
# measured while that fabric is blocked behind another lane's composition root.


def _seams_over(tmp_path: Path, recorder: Any) -> dict[str, Any]:
    entitlements = ControlPlaneRegistry()
    register_typed_at_composition(
        entitlements,
        product_entitlement_key(tenant_id=TENANT),
        ProductEntitlementPolicy(
            tenant_id=TENANT,
            policy_version="1.0.0",
            principals={
                CLIENT: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({"join.product"}),
                    permitted_roles=frozenset({ROLE}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    source = ControlPlaneProductEntitlementSource(control_plane=entitlements, clock=lambda: INSTANT)
    return authority(
        tenant=TENANT,
        key="join-wiring/mapping",
        grants={TOKEN: (CLIENT, (SCOPE_EVERYTHING,))},
        product_entitlement=source,
        perspective_resolver=lambda *, grant, tenant, requested_role: Perspective(
            principal_id=grant.client_id, role=ROLE
        ),
        refusal_recorder=recorder,
        clock_at=INSTANT,
    )


def _recorder_over(store: Any, registry: ControlPlaneRegistry) -> Any:
    return refusal_recorder(
        registry, store=store, tenant=TENANT, replay_record_class=REPLAY_RECORD_CLASS
    )


def _deps(registry: ControlPlaneRegistry, store: Any) -> ApiDependencies:
    return ApiDependencies(control_plane=registry, artifact_store=store, product_resolver=_resolver)


def test_a_recorder_over_a_store_not_declaring_its_class_is_refused_at_boot(tmp_path: Path) -> None:
    from ccf.artifacts.file_store import FileArtifactStore
    from ccf.artifacts.protocol import WriteKinds
    from ccf_runtime.http_api.app import GovernedWiringError

    registry = ControlPlaneRegistry()
    undeclared = FileArtifactStore(root=tmp_path / "undeclared", write_kinds=WriteKinds({}))
    with pytest.raises(GovernedWiringError, match=REPLAY_RECORD_CLASS):
        create_app(_deps(registry, undeclared), **_seams_over(tmp_path, _recorder_over(undeclared, registry)))


def test_a_recorder_over_a_store_exposing_no_declaration_is_refused_at_boot(tmp_path: Path) -> None:
    from ccf_runtime.http_api.app import GovernedWiringError

    class _Undeclaring:
        def __init__(self, inner: Any) -> None:
            self._inner = inner

        def put(self, authorized: Any, artifact: Any) -> Any:
            return self._inner.put(authorized, artifact)

        def get(self, *, content_address: str) -> bytes:
            return bytes(self._inner.get(content_address=content_address))

        def exists(self, *, content_address: str) -> bool:
            return bool(self._inner.exists(content_address=content_address))

        def resolve_uri(self, *, uri: str) -> str:
            return str(self._inner.resolve_uri(uri=uri))

    registry = ControlPlaneRegistry()
    opaque = _Undeclaring(deployment_store(tmp_path / "opaque", REPLAY_RECORD_CLASS))
    with pytest.raises(GovernedWiringError, match="write_kinds"):
        create_app(_deps(registry, opaque), **_seams_over(tmp_path, _recorder_over(opaque, registry)))


def test_the_same_recorder_over_a_declaring_store_builds(tmp_path: Path) -> None:
    registry = ControlPlaneRegistry()
    declared = deployment_store(tmp_path / "declared", REPLAY_RECORD_CLASS)
    assert create_app(_deps(registry, declared), **_seams_over(tmp_path, _recorder_over(declared, registry))) is not None


# --- the two src bridges the join carried, measured -------------------------------


def test_the_recorder_verifies_its_capability_at_construction() -> None:
    """A recorder handed a fabricated or wrong-kind capability dies at
    composition, not at the first denial (D-IMPL-353 §1.5c, g)."""
    from ccf.authz.capability import ArtifactWrite, CapabilityBypassError, ReplayMint
    from ccf.products.resolver import ReplayRefusalRecorder
    from tests.controlplane.capabilities import capability, fabrications

    # No store: the refusal fires before anything could touch one.
    store = None
    with pytest.raises(CapabilityBypassError):
        ReplayRefusalRecorder(
            authorized=capability(ArtifactWrite, tenant=TENANT, resource=f"{REPLAY_RECORD_CLASS}/x"),  # type: ignore[arg-type]
            artifact_store=store,  # type: ignore[arg-type]
            assembly_mode="algorithmic",
        )
    for name, forged in fabrications(ReplayMint, tenant=TENANT, resource=REPLAY_RECORD_CLASS):
        with pytest.raises(CapabilityBypassError):
            ReplayRefusalRecorder(authorized=forged, artifact_store=store, assembly_mode="algorithmic")  # type: ignore[arg-type]


def test_the_catalog_refuses_a_capability_for_another_entrys_key() -> None:
    """The entry's derived key may agree with the capability's resource and
    never supply it: a genuine capability for another key is refused before
    the registry is touched, and nothing registers."""
    from ccf.authz.capability import Register
    from tests.controlplane.capabilities import capability

    registry = ControlPlaneRegistry()
    catalog = SkillCatalog(registry)
    entry = parse_artifact(_load("skills/covenant_metrics_tool.yaml")["entry"], SKILL_CATALOG_ENTRY)
    other_key = f"{TENANT}/{SKILL_CATALOG_ENTRY.class_id}/some-other-entry"
    with pytest.raises(ValueError, match="derives key"):
        catalog.register(capability(Register, tenant=TENANT, resource=other_key), entry)  # type: ignore[arg-type]
    assert registry.keys_of_class(SKILL_CATALOG_ENTRY.class_id) == ()


def test_the_reverse_index_answers_nothing_for_a_string_that_is_not_an_address(tmp_path: Path) -> None:
    """`names_at` checks the shape before it opens the index (D-IMPL-345 S-02)."""
    store = deployment_store(tmp_path / "names")
    for malformed in ("../../../../etc/hostname", "/etc/hostname", ".artifact-names.json", "e" * 63, "E" * 64, ""):
        assert store.names_at(content_address=malformed) == ()
