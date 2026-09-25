"""The paved-road door registers through the composition recipe (D-IMPL-354; the join).

``ccf_runtime.mcp.product_door`` is a composition root (the §4 lint's
``COMPOSITION_MINT_SITES``). Opening a door composes a deployment's door, and
the two registrations that composition performs — the entitlement policy and
the scope mapping — are the deployment's own act: no served caller requests
them and no gate can mint for them. So the root records each decision on the
Control Plane's own audit log as a ``composition`` event naming the key, and
mints ``Register`` for exactly that key from that event. Measured here over a
structural :class:`~ccf_runtime.mcp.product_door.ServesProducts` stand-in, so
the proof needs no paved-road product (whose composition root is J-SRC's).

What would fail here: a door that registered with a bare key (the registry
refuses — the negative half is the registry's own test), or one that minted
one wildcard ``Register`` for both keys (each capability is bound to ONE key,
and the two audit events name two keys).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ccf.authz.capability import COMPOSITION_PRINCIPAL, Register
from ccf.controlplane.artifacts import (
    EgressDoorBinding,
    ProductClassDeclaration,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment.environment import (
    DoorEnvironment,
    EnvironmentDocument,
    EnvironmentValue,
    SubstrateSettings,
)
from ccf.products.entitlement import PRODUCT_ENTITLEMENT_POLICY, product_entitlement_key
from ccf.projection.plan import Perspective
from ccf_runtime.authz.artifact import SCOPE_MAPPING
from ccf_runtime.mcp.product_door import open_door, scope_mapping_key
from http_api.composition_authority import deployment_store, refusal_recorder

TENANT = "door-tenant"
PRINCIPAL = "door-principal"
ROLE = "door-role"
REPLAY_RECORD_CLASS = "ccf.decision-replay-record"


class _Product:
    """The nine structural members `ServesProducts` names, and nothing else."""

    def __init__(self, tmp_path: Path) -> None:
        self.tenant_id = TENANT
        self.declaration = ProductClassDeclaration.model_validate(
            {
                "semver": "1.0.0",
                "schema_name": "door.product",
                "schema_version": "1.0.0",
                "ttl_anchor": "from_decision",
                "assembly_mode": "algorithmic",
                "max_ttl_key": f"{TENANT}/max-ttl/door",
                "required_operator_keys": (f"{TENANT}/operators/door",),
            }
        )
        self.default_perspective = Perspective(principal_id=PRINCIPAL, role=ROLE)
        self.control_plane = ControlPlaneRegistry()
        self.refusal_recorder = refusal_recorder(
            self.control_plane,
            store=deployment_store(tmp_path / "replay", REPLAY_RECORD_CLASS),
            tenant=TENANT,
            replay_record_class=REPLAY_RECORD_CLASS,
        )
        self.door = EgressDoorBinding.model_validate(
            {
                "semver": "1.0.0",
                "required_scope": "door:scope",
                "tool_description": "a door fixture",
                "producer_id": "door-producer",
                "producer_tenant": TENANT,
            }
        )
        self.environment = EnvironmentDocument(
            substrate=SubstrateSettings(setting="DOOR_SCRATCH", prefix="door-", suffix=".sqlite3"),
            door=DoorEnvironment(
                credential=EnvironmentValue(from_env="DOOR_TOKEN", remedy="set it"),
                issuer_url=EnvironmentValue(from_env="DOOR_ISSUER", remedy="set it"),
                resource_server_url=EnvironmentValue(from_env="DOOR_RESOURCE", remedy="set it"),
            )
        )

    def resolve(self, **kwargs: Any) -> Any:  # pragma: no cover - never served here
        raise AssertionError("this fixture serves nothing")


def test_the_doors_two_registrations_are_each_minted_from_a_recorded_composition_decision(
    tmp_path: Path,
) -> None:
    product = _Product(tmp_path)
    before = len(product.control_plane.audit_log.events())
    door = open_door(product, environ={"DOOR_TOKEN": "t"})
    events = product.control_plane.audit_log.events()[before:]

    compositions = [e for e in events if e.action == "composition"]
    assert [e.key for e in compositions] == [
        product_entitlement_key(tenant_id=TENANT),
        scope_mapping_key(tenant_id=TENANT),
    ]
    assert all(e.actor == COMPOSITION_PRINCIPAL for e in compositions)
    assert all(e.version == Register.action_id for e in compositions)
    # Each decision precedes its own registration, and each registration was
    # audited under the composition principal — the registry read the actor
    # off the capability, never off a parameter.
    registrations = [e for e in events if e.action == "register_typed"]
    assert [e.key for e in registrations] == [e.key for e in compositions]
    assert all(e.actor == COMPOSITION_PRINCIPAL for e in registrations)
    # And both artifacts are resolvable at the versions the door pinned.
    assert door.tenant_id == TENANT
    assert product.control_plane.keys_of_class(PRODUCT_ENTITLEMENT_POLICY.class_id) == (
        product_entitlement_key(tenant_id=TENANT),
    )
    assert product.control_plane.keys_of_class(SCOPE_MAPPING.class_id) == (
        scope_mapping_key(tenant_id=TENANT),
    )


def test_the_decision_id_of_each_registration_is_its_own_composition_event(
    tmp_path: Path,
) -> None:
    """Two keys, two events, two capabilities: a boot-minted `Register` opens
    one key and is not a wildcard (§1.5). Measured by the registry's audit
    trail: each `register_typed` event follows exactly one `composition` event
    for the same key."""
    product = _Product(tmp_path)
    # The stub's own recorder recorded ITS composition decision (a ReplayMint)
    # on this log before the door opened; the door's trail starts here.
    before = len(product.control_plane.audit_log.events())
    open_door(product, environ={"DOOR_TOKEN": "t"})
    events = product.control_plane.audit_log.events()[before:]
    sequence = [(e.action, e.key) for e in events if e.action in {"composition", "register_typed"}]
    entitlement = product_entitlement_key(tenant_id=TENANT)
    mapping = scope_mapping_key(tenant_id=TENANT)
    assert sequence == [
        ("composition", entitlement),
        ("register_typed", entitlement),
        ("composition", mapping),
        ("register_typed", mapping),
    ]
    assert all(e.occurred_at.tzinfo is not None for e in events)
    assert datetime.now(UTC) >= max(e.occurred_at for e in events)
