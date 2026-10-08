"""Read-refusal attribution over HTTP — a refused read is bound to the tenant AND the principal that asked.

The HTTP twin of ``tests/mcp/test_read_refusal_attribution_mcp.py``; the module
docstring there states the finding and Dave's ruling of 2026-10-07 (*"Authorization
must bind the requesting tenant and principal together; a colliding principal id
in the door's tenant must not reveal another tenant's requested address. Check
existing records too."*).

The HTTP door is multi-tenant through one recorder whenever its authorizer
admits several tenants: the gate mints each evidence-read capability for the
verified grant's sole tenant (``SEC-002``), while
:func:`ccf_runtime.http_api.app.create_app` takes ONE ``refusal_recorder``. Here
the recorder is the fabric tenant's and writes into the store the evidence
routes serve, so a refusal's reference is resolvable through its own door — the
shape ``tests/http_api/test_evidence_dereference.py`` uses. The same client id,
``ALICE``, is a principal of both tenants, each at ``full``. All three routes
that call ``govern_dereference`` are asked: ``/replay/decisions``,
``/replay/resolutions`` and ``/artifact``.

Tenant, principal, class and token names are test deployment vocabulary,
meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.protocol import parse_artifact_uri
from ccf.authz.capability import ArtifactWrite
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.erasure import erasure_index_at
from ccf.products.disclosure import DISCLOSURE_FULL, DISCLOSURE_MINIMAL, DisclosureDecision
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf.replay.serve import ReplayWriter
from ccf_runtime.authz.delivery_boundary import SURFACE_HTTP_REPLAY_READ
from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource
from ccf_runtime.http_api.app import create_app
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import ERROR_EVIDENCE_ABSENT, ERROR_EVIDENCE_DISCLOSURE_WITHHELD
from http_api.composition_authority import composition_replay_mint, refusal_recorder, register_typed_at_composition
from http_api.conftest import Fabric
from tests.composition import declared_erasure_trust
from tests.controlplane.capabilities import capability
from tests.mcp.test_read_refusal_attribution_mcp import _record_as_written_before_the_binding

from .test_c2_tenant_hold_http import ROUTES, _assert_identical, _internal_cause
from .test_evidence_dereference import (
    AUDIT_INSTANT,
    REPLAY_RECORD_CLASS,
    Governed,
    _get_artifact,
    _get_record,
    _get_uri,
    same_shell,
)

#: The second tenant this door admits. The first is the fabric's own.
FOREIGN = "refusal-other-tenant"
#: ONE client id, a principal of BOTH tenants — the collision the ruling names.
ALICE = "refusal-shared-client-id"
#: A second principal of ``FOREIGN``, whose genuine record ``FOREIGN``'s ``ALICE``
#: may not read (hold 1) — the subject of the disclosure oracle.
BOB = "refusal-other-principal"
ROLE = "refusal-role"
OWN_TOKEN = "refusal-token-own"
FOREIGN_TOKEN = "refusal-token-foreign"

#: The address ``FOREIGN``'s principal asks about. Nothing is ever stored there.
ASKED = "a" * 64

#: The address a forged read-refusal record claims the door tenant's ``ALICE``
#: asked about — an ask she never made.
FORGED_ASK = "f" * 64

#: A client-lane class: one the store does not declare under ``ReplayMint``.
CLIENT_CLASS = "c"


def _policy(tenant: str, product_class: str, level: str) -> ProductEntitlementPolicy:
    return ProductEntitlementPolicy(
        tenant_id=tenant,
        policy_version="1.0.0",
        principals={
            ALICE: ProductEntitlementGrant(
                permitted_schema_names=frozenset({product_class}),
                permitted_roles=frozenset({ROLE}),
                disclosure_level=level,
            )
        },
        disclosure_level=DISCLOSURE_MINIMAL,
        # Dave's Q12 (`D-IMPL-378`): owner read-back is default-deny behind an
        # explicit tenant class allowlist; this suite is about hold 3, so its
        # governed class is listed (and its records carry the affirmation).
        evidence_readable_classes=frozenset({product_class}),
    )


def _door(root: Path, *, own_level: str = DISCLOSURE_FULL, foreign_level: str = DISCLOSURE_FULL) -> Governed:
    """One HTTP app admitting the fabric's tenant and ``FOREIGN``, ONE recorder of the fabric's tenant."""
    from ccf_runtime.http_api.auth import BearerTokenAuth

    from .gate_fixtures import SCOPE_EVERYTHING, tenanted_source, wide_authorizer

    fabric = Fabric(root / "fabric")
    door_tenant = fabric.product_address.tenant
    product_class = fabric.product_address.product_class
    registry = ControlPlaneRegistry()
    for tenant, level in ((door_tenant, own_level), (FOREIGN, foreign_level)):
        register_typed_at_composition(
            registry, product_entitlement_key(tenant_id=tenant), _policy(tenant, product_class, level), PRODUCT_ENTITLEMENT_POLICY
        )
    source = ControlPlaneProductEntitlementSource(control_plane=registry, clock=lambda: AUDIT_INSTANT)
    recorder = refusal_recorder(
        registry,
        store=fabric.store,
        tenant=door_tenant,
        replay_record_class=REPLAY_RECORD_CLASS,
        assembly_mode="algorithmic",
        policy_bundle_pin=None,
        disclosure_level_for=source.disclosure_level_for,
    )
    erasure_index = erasure_index_at(root / "erasure")
    app = create_app(
        ApiDependencies(
            control_plane=registry,
            artifact_store=fabric.store,
            erasure_trust=declared_erasure_trust(),
            erasure_index=erasure_index,
            product_resolver=fabric.product_resolver,
        ),
        auth=BearerTokenAuth(
            token_source=tenanted_source(
                {
                    OWN_TOKEN: (ALICE, (SCOPE_EVERYTHING,), door_tenant),
                    FOREIGN_TOKEN: (ALICE, (SCOPE_EVERYTHING,), FOREIGN),
                },
                tenant=door_tenant,
            )
        ),
        authorizer=wide_authorizer(tenant=(door_tenant, FOREIGN), key="refusal/scope-mapping"),
        product_entitlement=source,
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role=requested_role if requested_role is not None else ROLE
            )
        ),
        refusal_recorder=recorder,
        replay_record_product_class=None,
    )
    return Governed(
        app=app,
        store=fabric.store,
        recorder=recorder,
        registry=registry,
        tenant=door_tenant,
        product_class=product_class,
        erasure_index=erasure_index,
    )


def _refused_reference(door: Governed) -> str:
    """``FOREIGN``'s ``ALICE`` asks ``/replay/decisions`` for ``ASKED``; the replay reference its refusal hands back."""
    refused = _get_record(door, ASKED, token=FOREIGN_TOKEN)
    assert refused.status_code == 404, refused.text
    return str(refused.json()["refusal"]["replay_reference"])


def _answers(door: Governed, reference: str, *, token: str) -> dict[str, Any]:
    address = parse_artifact_uri(reference).artifact_version
    return {
        "decisions": _get_record(door, address, token=token),
        "resolutions": _get_uri(door, reference, token=token),
        "artifact": _get_artifact(door, address, token=token),
    }


def _served_record(door: Governed, *, tenant: str, principal: str = ALICE) -> str:
    """A served record of ``tenant`` for ``principal``, filed by ``tenant``'s own record writer."""
    from http_api.conftest import _replay_record

    base = _replay_record()
    served = base.content_generation_path.model_copy(
        update={
            "request": ProductRequest(
                schema_name=door.product_class,
                schema_version="1.0.0",
                subject="read-refusal-attribution",
                intent="intent-1",
                freshness="event-driven",
                asked_at=AUDIT_INSTANT,
                parameters={},
            ),
            # Dave's Q12 (`D-IMPL-378`): the deciding class's affirmation that
            # its answers never withhold their subject, which read-back needs.
            "subject_withholding": "never",
        }
    )
    record = base.model_copy(
        update={
            "tenant_id": tenant,
            "perspective_conditioning": base.perspective_conditioning.model_copy(
                update={"principal_id": principal, "role": ROLE}
            ),
            "content_generation_path": served,
        }
    )
    return (
        ReplayWriter(
            authorized=composition_replay_mint(door.registry, tenant=tenant, artifact_class=REPLAY_RECORD_CLASS),
            store=door.store,
        )
        .write_replay_record(record=record)
        .replay_ref.content_address
    )


def test_another_tenants_read_refusal_record_answers_a_colliding_principal_as_a_missing_address_does(
    tmp_path: Path,
) -> None:
    """``FOREIGN``'s ``ALICE`` is refused a read; the fabric tenant's ``ALICE`` —
    same client id, ``full`` — asks every evidence route for that read-refusal
    record. Each must answer exactly what it answered while nothing was filed
    there — status, bytes and headers — with the recorded absence behind it and
    nothing of ``FOREIGN``'s ask in it. A twin door, built identically over its
    own store, mints the record first, so its reference is known in advance."""
    reference = _refused_reference(_door(tmp_path / "twin"))

    door = _door(tmp_path / "door")
    before = _answers(door, reference, token=OWN_TOKEN)
    assert _refused_reference(door) == reference, "the twin door minted another record"
    after = _answers(door, reference, token=OWN_TOKEN)

    _assert_identical(before, after)
    for route in ROUTES:
        assert _internal_cause(door, after[route]) == ("nonexistent", ERROR_EVIDENCE_ABSENT), route
        assert ASKED not in after[route].text, route


def test_the_refused_principal_of_another_tenant_cannot_read_its_record_back_through_this_door(
    tmp_path: Path,
) -> None:
    """Said plainly: the record is decided under ``FOREIGN`` and filed under the
    recorder's tenant, and the governed read serves a record only where it is
    filed under the tenant it was decided under — so ``FOREIGN``'s ``ALICE``
    cannot read it back through this door (nor could it before the binding:
    hold 0 refused it then)."""
    door = _door(tmp_path)
    reference = _refused_reference(door)

    answers = _answers(door, reference, token=FOREIGN_TOKEN)
    for route in ROUTES:
        assert _internal_cause(door, answers[route]) == ("nonexistent", ERROR_EVIDENCE_ABSENT), route


def test_a_principal_of_the_recorders_tenant_still_reads_its_own_read_refusal_record(tmp_path: Path) -> None:
    """``D-IMPL-345`` R-2 on the multi-tenant door: the fabric tenant's ``ALICE``
    reads back its own read refusal by address and by URI."""
    door = _door(tmp_path)
    refused = _get_record(door, ASKED, token=OWN_TOKEN)
    reference = refused.json()["refusal"]["replay_reference"]

    for response in (
        _get_record(door, parse_artifact_uri(reference).artifact_version, token=OWN_TOKEN),
        _get_uri(door, reference, token=OWN_TOKEN),
    ):
        assert response.status_code == 200, response.text
        assert response.json()["perspective_conditioning"]["principal_id"] == ALICE


def test_hold_three_reads_the_level_in_force_for_the_requesting_tenant_not_the_recorders(
    tmp_path: Path,
) -> None:
    """``FOREIGN``'s ``ALICE`` reads its own record, filed by ``FOREIGN``'s writer,
    through this door: it crosses at ``FOREIGN``'s level for ``ALICE`` and never at
    the level the recorder's tenant declares for its own ``ALICE``."""
    upgrade = _door(tmp_path / "upgrade", own_level=DISCLOSURE_FULL, foreign_level=DISCLOSURE_MINIMAL)
    withheld = _get_record(upgrade, _served_record(upgrade, tenant=FOREIGN), token=FOREIGN_TOKEN)
    assert withheld.status_code == 404, (
        "the recorder's tenant's level for a colliding principal id disclosed another tenant's record"
    )
    assert _internal_cause(upgrade, withheld) == ("unauthorized", ERROR_EVIDENCE_DISCLOSURE_WITHHELD)

    downgrade = _door(tmp_path / "downgrade", own_level=DISCLOSURE_MINIMAL, foreign_level=DISCLOSURE_FULL)
    crossed = _get_record(downgrade, _served_record(downgrade, tenant=FOREIGN), token=FOREIGN_TOKEN)
    assert crossed.status_code == 200, (
        "the recorder's tenant's level for a colliding principal id withheld the caller's own record"
    )


def _disclosure_decision(door: Governed, response: Any) -> tuple[str, str | None]:
    """The level the recorder applied to a refusal, and the policy key that set it — from the RECORD."""
    reference = response.json()["refusal"]["replay_reference"]
    record = door.record_at(door.store.resolve_uri(uri=reference))
    decision = DisclosureDecision.model_validate_json(record.content_generation_path.disclosure_decision)
    return decision.level, decision.policy.identity if decision.policy is not None else None


def test_a_refusal_of_another_tenants_principal_is_disclosed_at_its_own_level_not_the_recorders(
    tmp_path: Path,
) -> None:
    """The level the door's recorder discloses a refusal shell at is read under
    the refused caller's own tenant: ``FOREIGN``'s ``ALICE`` at ``minimal`` gets
    one shell for a missing address and for another ``FOREIGN`` principal's
    genuine record, whatever the recorder's tenant declares for its own
    ``ALICE``; and, the other way round, its own ``full``."""
    upgrade = _door(tmp_path / "upgrade", own_level=DISCLOSURE_FULL, foreign_level=DISCLOSURE_MINIMAL)
    nowhere, others = "b" * 64, _served_record(upgrade, tenant=FOREIGN, principal=BOB)
    missing = _get_record(upgrade, nowhere, token=FOREIGN_TOKEN)
    poached = _get_record(upgrade, others, token=FOREIGN_TOKEN)
    for response in (missing, poached):
        assert _disclosure_decision(upgrade, response) == (
            DISCLOSURE_MINIMAL,
            product_entitlement_key(tenant_id=FOREIGN),
        ), "a refusal of another tenant's principal was disclosed under the recorder's tenant's level"
    assert same_shell(missing, nowhere, poached, others)

    downgrade = _door(tmp_path / "downgrade", own_level=DISCLOSURE_MINIMAL, foreign_level=DISCLOSURE_FULL)
    assert _disclosure_decision(downgrade, _get_record(downgrade, nowhere, token=FOREIGN_TOKEN)) == (
        DISCLOSURE_FULL,
        product_entitlement_key(tenant_id=FOREIGN),
    )


# =========================================================================
# "Check existing records too" — Dave, 2026-10-07 19:31 (Q3); the MCP twin
# states the ruling.
# =========================================================================


def _record_before_the_marker(door: Governed) -> str:
    """The door tenant's ``ALICE`` refused ``ASKED`` on ``/replay/decisions``, as the door filed it before the marker; its reference."""
    return _record_as_written_before_the_binding(
        door.recorder,
        principal=ALICE,
        reference=ASKED,
        surface=SURFACE_HTTP_REPLAY_READ,
        address="/replay/decisions",
        determined_at=AUDIT_INSTANT,
    ).replay_reference


def test_a_read_refusal_record_written_before_the_marker_reads_as_missing_for_everyone(tmp_path: Path) -> None:
    """Every route answers an unmarked read-refusal record exactly as it
    answered the address while nothing was filed there — for the owner it
    names (the loss of owner read-back) and for another tenant's principal
    with the owner's client id — with the recorded absence behind it."""
    reference = _record_before_the_marker(_door(tmp_path / "twin"))

    door = _door(tmp_path / "door")
    readers = {"owner": OWN_TOKEN, "other-tenant": FOREIGN_TOKEN}
    before = {who: _answers(door, reference, token=token) for who, token in readers.items()}
    assert _record_before_the_marker(door) == reference, "the twin door minted another record"

    for who, token in readers.items():
        after = _answers(door, reference, token=token)
        _assert_identical(before[who], after)
        for route in ROUTES:
            assert _internal_cause(door, after[route]) == ("nonexistent", ERROR_EVIDENCE_ABSENT), (who, route)
            assert ASKED not in after[route].text, (who, route)


@pytest.mark.parametrize("forger", ["another-tenant", "the-door-tenant"])
def test_a_marked_read_refusal_record_filed_on_a_client_lane_answers_as_a_missing_address_does(
    tmp_path: Path, forger: str
) -> None:
    """Caller-supplied bytes cannot confer trust (Q3). The record the governed
    read writes, MARKED, for the door tenant's ``ALICE`` asking ``FORGED_ASK`` —
    minted on a scratch door — is filed on a client lane of this door's store,
    where ``ALICE`` never asked it; every route answers her exactly as before
    the filing."""
    scratch = _door(tmp_path / "scratch")
    reference = _get_record(scratch, FORGED_ASK, token=OWN_TOKEN).json()["refusal"]["replay_reference"]
    internal = scratch.internal(reference)
    assert internal.resource is not None and internal.resource.tenant_from == "capability", (
        "the governed read minted no marker"
    )
    address = parse_artifact_uri(reference).artifact_version
    document = json.loads(scratch.store.get(content_address=address))

    door = _door(tmp_path / "door")
    before = _answers(door, reference, token=OWN_TOKEN)
    filed = door.store.put(
        capability(
            ArtifactWrite,
            tenant=FOREIGN if forger == "another-tenant" else door.tenant,
            resource=f"{CLIENT_CLASS}/forged-read-refusal",
        ),
        document,
    )
    assert filed.content_address == address
    after = _answers(door, reference, token=OWN_TOKEN)

    _assert_identical(before, after)
    for route in ROUTES:
        assert _internal_cause(door, after[route]) == ("nonexistent", ERROR_EVIDENCE_ABSENT), route
