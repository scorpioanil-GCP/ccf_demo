"""A forged record over MCP — bytes the fabric's record writer did not file are never read as a record.

The re-review of the ``D-IMPL-376`` close-out (confirmed by the coordinator):
:func:`ccf_runtime.authz.delivery_boundary.govern_dereference` takes the
record's tenant and principal from the BYTES stored at the address and never
checks that the address was filed by the fabric's own record writer. Tenant B
files, on its own client lane with an ordinary ``ArtifactWrite``, the canonical
bytes of a ``DecisionReplayRecord`` claiming tenant A and A's principal; the MCP
artifact server's split sends A's read of that address (A filed nothing there)
to the governed dereference, which served the forgery as A's evidence.

Dave's ruling: the governed read serves a record only if the store shows it was
filed by the fabric's own record writer — under a class the store's
``WriteKinds`` declares under ``ReplayMint`` — under the tenant the record
claims; anything else answers EXACTLY like a missing address; a store that
cannot answer that question refuses rather than serves.

**A same-tenant forgery answers as a missing address too** (the client-lane
ruling, ``D-IMPL-378``). Bytes a principal of tenant A files on A's OWN client
lane are served to A's principals by the split's client lane (C8;
``D-IMPL-353`` §2 P5: the §7.4 transport round-trips every artifact class) —
except bytes that validate as a ``DecisionReplayRecord``, the validator every
SDK record reader applies. Dave's ruling: such bytes stay ordinary client
artifacts only if their untrusted origin is explicit and consumers cannot
accept them as governed evidence, otherwise that path is refused until
provenance is enforced. Neither held, so the split decides them through the
governed dereference, which answers them exactly as a missing address (its
provenance check; for a record claiming another tenant, its tenant hold). What
a consumer of the MCP-backed store does with them is
``tests/mcp/test_clientlane_record_shaped.py``.

Tenant, principal, class, scope and token names are test deployment
vocabulary, meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.authz.capability import ArtifactRead, ArtifactWrite
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.erasure import compose_erasure_consult
from ccf_runtime.authz.delivery_boundary import SURFACE_MCP_RESOURCE, DereferenceRequest, govern_dereference
from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource
from ccf_runtime.http_api.errors import ERROR_EVIDENCE_ABSENT
from tests.composition import declared_erasure_trust, no_erasures
from tests.controlplane.capabilities import capability
from tests.http_api.composition_authority import deployment_store, refusal_recorder, register_typed_at_composition
from tests.mcp.guarded_servers import AUDIT_INSTANT, FOREIGN, PRINCIPAL, REPLAY_RECORD_CLASS, TENANT
from tests.mcp.test_c2_tenant_hold_mcp import (
    SURFACES,
    _answers,
    _assert_identical,
    _file,
    _internal_cause,
    _policy,
    _read,
    _record,
    _world,
)

CLIENT_CLASS = "c"


def _forge_on(world: Any, record: Any, *, forger_tenant: str) -> str:
    """``forger_tenant`` files the forged record's bytes on its own client lane."""
    filed = world.store.put(
        capability(ArtifactWrite, tenant=forger_tenant, resource=f"{CLIENT_CLASS}/innocuous"),
        json.loads(canonical_bytes(record)),
    )
    return str(filed.content_address)


def test_a_record_forged_on_another_tenants_client_lane_answers_as_a_missing_address_does(
    tmp_path: pathlib.Path,
) -> None:
    world = _world(tmp_path)
    forged = _record(tenant=TENANT, principal=PRINCIPAL, subject="cross-tenant-forgery")
    address = content_hash(forged)
    before = _answers(world, address)

    assert _forge_on(world, forged, forger_tenant=FOREIGN) == address
    after = _answers(world, address)

    assert after["blob"] != canonical_bytes(forged), "a forged record crossed as governed evidence"
    _assert_identical(before, after)
    for surface in SURFACES:
        assert _internal_cause(world, after[surface]) == ("nonexistent", ERROR_EVIDENCE_ABSENT), surface
    # Control: a record the fabric's own writer filed still reads for its owner.
    genuine = _record(tenant=TENANT, principal=PRINCIPAL, subject="genuine")
    assert _read(world, "blob", _file(world, genuine)) == canonical_bytes(genuine)


def test_a_record_forged_on_the_tenants_own_client_lane_answers_as_a_missing_address_does(
    tmp_path: pathlib.Path,
) -> None:
    """A principal of the reader's own tenant files, on that tenant's client lane,
    the canonical bytes of a record claiming the reader. Blob and presence answer
    what they answered while the address was empty, and the determination recorded
    behind each is the governed dereference's ``nonexistent`` /
    ``evidence-absent``. Controls: an ordinary artifact on the same client lane
    still crosses as its exact bytes, and a record the fabric's own writer filed
    still reads for its owner."""
    world = _world(tmp_path)
    forged = _record(tenant=TENANT, principal=PRINCIPAL, subject="same-tenant-forgery")
    address = content_hash(forged)
    before = _answers(world, address)

    assert _forge_on(world, forged, forger_tenant=TENANT) == address
    after = _answers(world, address)

    assert after["blob"] != canonical_bytes(forged), "a same-tenant forgery crossed the client lane"
    _assert_identical(before, after)
    for surface in SURFACES:
        assert _internal_cause(world, after[surface]) == ("nonexistent", ERROR_EVIDENCE_ABSENT), surface
    plain = {"note": "an ordinary client-lane artifact"}
    filed = world.store.put(capability(ArtifactWrite, tenant=TENANT, resource=f"{CLIENT_CLASS}/plain"), plain)
    assert _read(world, "blob", str(filed.content_address)) == canonical_bytes(plain)
    genuine = _record(tenant=TENANT, principal=PRINCIPAL, subject="genuine")
    assert _read(world, "blob", _file(world, genuine)) == canonical_bytes(genuine)


class _WithoutNaming:
    """A third-party substrate that cannot say who filed an address: it keeps the
    four Protocol verbs and drops one of the two readings the attribution needs."""

    def __init__(self, inner: FileArtifactStore, *, drop: str) -> None:
        self._inner = inner
        self._drop = drop

    def __getattr__(self, attribute: str) -> Any:
        if attribute == self._drop:
            raise AttributeError(attribute)
        return getattr(self._inner, attribute)


@pytest.mark.parametrize("drop", ["names_at", "write_kinds"])
def test_a_store_that_cannot_attribute_an_address_refuses_rather_than_serves(
    tmp_path: pathlib.Path, drop: str
) -> None:
    """A genuine record, read by its owner, over a store that cannot answer whether
    the fabric's record writer filed the address: the read is refused by name
    (a wiring defect, raised before anything is recorded), never served."""
    registry = ControlPlaneRegistry()
    register_typed_at_composition(registry, _policy_key(), _policy(TENANT), _policy_class())
    source = ControlPlaneProductEntitlementSource(control_plane=registry, clock=lambda: AUDIT_INSTANT)
    recorded = deployment_store(tmp_path / "replay", REPLAY_RECORD_CLASS)
    recorder = refusal_recorder(
        registry, store=recorded, tenant=TENANT, replay_record_class=REPLAY_RECORD_CLASS,
        assembly_mode="algorithmic", policy_bundle_pin=None, disclosure_level_for=source.disclosure_level_for,
    )
    inner = deployment_store(tmp_path / "artifacts", REPLAY_RECORD_CLASS)
    world = type("W", (), {"store": inner})()
    genuine = _record(tenant=TENANT, principal=PRINCIPAL, subject="genuine-over-an-unattributing-store")
    address = _file(world, genuine)
    consulted = compose_erasure_consult(
        _WithoutNaming(inner, drop=drop),  # type: ignore[arg-type]
        index=no_erasures(),
        audit_log=ControlPlaneRegistry().audit_log,
        clock=lambda: AUDIT_INSTANT,
        control_plane=ControlPlaneRegistry(),
        erasure_trust=declared_erasure_trust(),
    )
    records_before = sorted(str(path) for path in (tmp_path / "replay").rglob("*"))

    with pytest.raises(TypeError) as refused:
        govern_dereference(
            capability(ArtifactRead, tenant=TENANT, resource=address, principal=PRINCIPAL),
            reference=DereferenceRequest(reference=address, by_uri=False, wants_bytes=True),
            store=consulted,
            entitlement_source=source,
            refusal_recorder=recorder,
            audit_log=ControlPlaneRegistry().audit_log,
            surface=SURFACE_MCP_RESOURCE,
            address=f"ccf-artifact-blob://{address}",
        )
    assert type(refused.value).__name__ == "UnattributableDeliveryBoundaryError"
    assert sorted(str(path) for path in (tmp_path / "replay").rglob("*")) == records_before, "nothing is recorded"


def _policy_key() -> str:
    from ccf.products.entitlement import product_entitlement_key

    return product_entitlement_key(tenant_id=TENANT)


def _policy_class() -> Any:
    from ccf.products.entitlement import PRODUCT_ENTITLEMENT_POLICY

    return PRODUCT_ENTITLEMENT_POLICY
