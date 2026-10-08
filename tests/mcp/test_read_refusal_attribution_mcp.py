"""Read-refusal attribution over MCP — a refused read is bound to the tenant AND the principal that asked.

:func:`ccf_runtime.authz.delivery_boundary.govern_dereference` records every
refused read through the door's ``refusal_recorder``. The re-review of the
``D-IMPL-376`` close-out measured that the read-refusal record named the DOOR
RECORDER's tenant as the tenant the read was decided under, whichever tenant the
refused caller's capability named. The MCP artifact server serves several tenants
through one recorder, so a principal holding a capability for the recorder's
tenant, with the same client id as a principal of ANOTHER tenant, passed hold 0
(the tenant) and hold 1 (the principal id) on that other principal's read-refusal
record — hold 2 does not apply to a record the boundary itself wrote — and read
the address the other principal had asked for.

Dave's ruling (2026-10-07, the work this module belongs to is ``D-IMPL-378``):
*"Authorization must bind the requesting tenant and principal together; a
colliding principal id in the door's tenant must not reveal another tenant's
requested address. Check existing records too."*

The world every case uses is the shape the MCP artifact server is built in: ONE
store behind the server and behind the door's recorder (so a refusal's reference
is resolvable through its own door, as ``D-IMPL-345`` wires it), one recorder of
``TENANT``, and an authorizer admitting both ``TENANT`` and ``FOREIGN``. The same
client id, ``ALICE``, is a principal of both tenants.

Tenant, principal, class, scope and token names are test deployment vocabulary,
meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import anyio
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

from ccf.artifacts.protocol import parse_artifact_uri
from ccf.authz.capability import ArtifactRead, ArtifactWrite
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.erasure import compose_erasure_consult
from ccf.products.disclosure import DISCLOSURE_FULL, DISCLOSURE_MINIMAL, DisclosureDecision
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.refusal import (
    RefusalEnvelope,
    RequestIdentity,
    ResourceRequestIdentity,
    SubjectUnavailableRefusal,
    envelope_for,
)
from ccf.products.request import ProductRequest
from ccf.products.resolver import ReplayRefusalRecorder
from ccf.projection.plan import Perspective
from ccf.replay.engine import RefusalReplayOutcome, replay_refusal
from ccf.replay.record import NO_ROLE_RESOLVED, DecisionReplayRecord, ResolutionNotApplicable
from ccf.replay.serve import ReplayWriter
from ccf_runtime.authz.delivery_boundary import (
    DEREFERENCE_PRODUCT_ID,
    SURFACE_MCP_RESOURCE,
    DereferenceRequest,
    govern_dereference,
)
from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource
from ccf_runtime.http_api.errors import ERROR_EVIDENCE_ABSENT, ERROR_EVIDENCE_DISCLOSURE_WITHHELD
from ccf_runtime.mcp.artifact_server import artifact_blob_uri, artifact_meta_uri, build_artifact_server
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource, TokenGrant
from tests.composition import declared_erasure_trust, no_erasures
from tests.controlplane.capabilities import capability
from tests.http_api.composition_authority import (
    composition_replay_mint,
    deployment_store,
    refusal_recorder,
    register_typed_at_composition,
)
from tests.mcp.guarded_servers import (
    AUDIT_INSTANT,
    FOREIGN,
    PRODUCT_CLASS,
    REPLAY_RECORD_CLASS,
    SCOPE,
    TENANT,
    authorizer_granting,
)
from tests.mcp.test_artifact_server_authorized import _as_grant
from tests.mcp.test_c2_tenant_hold_mcp import SURFACES, _assert_identical, _internal_cause

#: ONE client id, a principal of BOTH tenants — the collision the ruling names.
ALICE = "refusal-shared-client-id"
#: A second principal of ``FOREIGN``, whose genuine record ``FOREIGN``'s ``ALICE``
#: may not read (hold 1) — the subject of the disclosure oracle.
BOB = "refusal-other-principal"
ROLE = "refusal-role"

#: The verified callers: the same client id under each tenant.
OWN_ALICE = TokenGrant(client_id=ALICE, scopes=(SCOPE,), tenants=frozenset({TENANT}))
FOREIGN_ALICE = TokenGrant(client_id=ALICE, scopes=(SCOPE,), tenants=frozenset({FOREIGN}))
#: Another principal of the recorder's tenant: neither the owner of a record nor its collision.
OWN_BOB = TokenGrant(client_id=BOB, scopes=(SCOPE,), tenants=frozenset({TENANT}))

#: The address ``FOREIGN``'s principal asks about. Nothing is ever stored there:
#: the answer is a read refusal, and this string is what that record must not
#: carry to anyone else.
ASKED = "a" * 64

#: The address a forged read-refusal record claims ``TENANT``'s ``ALICE`` asked
#: about — an ask ``ALICE`` never made.
FORGED_ASK = "f" * 64

#: A client-lane class: one the store does not declare under ``ReplayMint``.
CLIENT_CLASS = "c"

#: The internal prose the shipped writer at ``7bf069cc`` gave every absence it
#: recorded, transcribed for :func:`_record_as_written_before_the_binding`.
_ABSENT_AT_7BF069CC = "the requested evidence is not available to this principal"


def _policy(tenant: str, level: str) -> ProductEntitlementPolicy:
    return ProductEntitlementPolicy(
        tenant_id=tenant,
        policy_version="1.0.0",
        principals={
            ALICE: ProductEntitlementGrant(
                permitted_schema_names=frozenset({PRODUCT_CLASS}),
                permitted_roles=frozenset({ROLE}),
                disclosure_level=level,
            )
        },
        disclosure_level=DISCLOSURE_MINIMAL,
    )


class _World:
    """One door serving ``TENANT`` and ``FOREIGN`` through ONE recorder of ``TENANT``, over ONE store."""

    def __init__(self, root: pathlib.Path, *, own_level: str = DISCLOSURE_FULL, foreign_level: str = DISCLOSURE_FULL) -> None:
        self.registry = ControlPlaneRegistry()
        for tenant, level in ((TENANT, own_level), (FOREIGN, foreign_level)):
            register_typed_at_composition(
                self.registry, product_entitlement_key(tenant_id=tenant), _policy(tenant, level), PRODUCT_ENTITLEMENT_POLICY
            )
        self.source = ControlPlaneProductEntitlementSource(control_plane=self.registry, clock=lambda: AUDIT_INSTANT)
        self.store = deployment_store(root / "one-store", REPLAY_RECORD_CLASS)
        #: What the shared C-2 helpers read a shell's record from: the same store.
        self.recorded = self.store
        self.recorder: ReplayRefusalRecorder = refusal_recorder(
            self.registry,
            store=self.store,
            tenant=TENANT,
            replay_record_class=REPLAY_RECORD_CLASS,
            assembly_mode="algorithmic",
            policy_bundle_pin=None,
            disclosure_level_for=self.source.disclosure_level_for,
        )
        self.server = build_artifact_server(
            server_name="read-refusal-attribution",
            store=self.store,
            token_verifier=SourceBackedTokenVerifier(
                source=StaticTokenSource(grants={"own": OWN_ALICE, "foreign": FOREIGN_ALICE})
            ),
            auth_settings=AuthSettings(
                issuer_url=AnyHttpUrl("https://issuer.invalid"),
                resource_server_url=AnyHttpUrl("https://artifact.invalid/mcp"),
                required_scopes=[SCOPE],
            ),
            authorizer=authorizer_granting(tenants=(TENANT, FOREIGN)),
            entitlement_source=self.source,
            refusal_recorder=self.recorder,
            audit_log=ControlPlaneRegistry().audit_log,
            erasure_trust=declared_erasure_trust(),
            erasure_index=no_erasures(),
            control_plane=ControlPlaneRegistry(),
        )

    def served_record(self, *, tenant: str, principal: str) -> str:
        """A served record of ``tenant`` for ``principal``, filed by ``tenant``'s own record writer."""
        from http_api.conftest import _replay_record

        base = _replay_record()
        served = base.content_generation_path.model_copy(
            update={
                "request": ProductRequest(
                    schema_name=PRODUCT_CLASS,
                    schema_version="1.0.0",
                    subject="read-refusal-attribution",
                    intent="intent-1",
                    freshness="event-driven",
                    asked_at=AUDIT_INSTANT,
                    parameters={},
                )
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
                authorized=composition_replay_mint(
                    ControlPlaneRegistry(), tenant=tenant, artifact_class=REPLAY_RECORD_CLASS
                ),
                store=self.store,
            )
            .write_replay_record(record=record)
            .replay_ref.content_address
        )


def _read(world: _World, grant: TokenGrant, surface: str, address: str) -> bytes:
    uri = (artifact_blob_uri if surface == "blob" else artifact_meta_uri)(content_address=address)
    reset = _as_grant(grant)
    try:
        (answer,) = list(anyio.run(world.server.read_resource, uri))
    finally:
        auth_context_var.reset(reset)
    content = answer.content
    return content if isinstance(content, bytes) else content.encode("utf-8")


def _answers(world: _World, grant: TokenGrant, address: str) -> dict[str, bytes]:
    return {surface: _read(world, grant, surface, address) for surface in SURFACES}


def _record_address(shell: bytes | RefusalEnvelope) -> str:
    """The content address of the read-refusal record behind a disclosed shell."""
    envelope = shell if isinstance(shell, RefusalEnvelope) else RefusalEnvelope.model_validate_json(shell)
    return parse_artifact_uri(envelope.replay_reference).artifact_version


def _record_at(world: _World, address: str) -> tuple[DecisionReplayRecord, RefusalEnvelope]:
    record = DecisionReplayRecord.model_validate_json(world.store.get(content_address=address))
    return record, RefusalEnvelope.model_validate_json(record.content_generation_path.assembly_refusal)


def _disclosure_decision(world: _World, shell: bytes) -> tuple[str, str | None]:
    """The level the recorder applied to a shell, and the policy key that set it — from the RECORD."""
    record, _ = _record_at(world, _record_address(shell))
    decision = DisclosureDecision.model_validate_json(record.content_generation_path.disclosure_decision)
    return decision.level, decision.policy.identity if decision.policy is not None else None


def _without_the_ask(shell: bytes, ask: str) -> dict[str, Any]:
    """A shell as a consumer compares it: its request held to the constant shape carrying its own ask, then dropped with its replay reference."""
    body = json.loads(shell)
    assert body.pop("request") == {
        "product_id": DEREFERENCE_PRODUCT_ID,
        "product_version": None,
        "parameters": {"reference": ask},
        "temporal_boundary": None,
    }
    body.pop("replay_reference")
    return dict(body)


def _record_as_written_before_the_binding(
    recorder: ReplayRefusalRecorder,
    *,
    principal: str,
    reference: str,
    surface: str = SURFACE_MCP_RESOURCE,
    address: str | None = None,
    determined_at: Any = AUDIT_INSTANT,
) -> RefusalEnvelope:
    """A read refusal of ``reference`` for ``principal``, minted exactly as the shipped writer at ``7bf069cc`` minted it.

    Not a hand-edited record: the same two seams ``govern_dereference``'s
    ``refuse`` called at ``7bf069cc`` for an absence — ``envelope_for`` over the
    ``nonexistent`` / ``evidence-absent`` determination, then the door's own
    ``recorder.record`` — with the value that writer chose: the resource
    identity's ``tenant_id`` was the RECORDER's tenant, whichever tenant the
    refused capability named, and no marker. Called for a principal of another
    tenant, this is that principal's read-refusal record as the door filed it
    before the binding; for the recorder's own tenant's principal, it is the
    record the door filed before the marker. Byte-identity with the shipped
    writer's output was measured at the red commit of ``D-IMPL-378`` lane
    378-refusal, for the MCP blob surface; ``surface``, ``address`` and
    ``determined_at`` are the door's own values on another surface.
    """
    envelope = envelope_for(
        SubjectUnavailableRefusal(cause="nonexistent", detail=_ABSENT_AT_7BF069CC, error_code=ERROR_EVIDENCE_ABSENT),
        request=RequestIdentity(
            product_id=DEREFERENCE_PRODUCT_ID,
            product_version=None,
            parameters={"reference": reference},
            temporal_boundary=None,
        ),
        resource=ResourceRequestIdentity(
            surface=surface,
            address=address if address is not None else artifact_blob_uri(content_address=reference),
            tenant_id=recorder.tenant_id,
            determined_at=determined_at,
        ),
        policy_bindings=(),
    )
    return recorder.record(
        envelope,
        perspective=Perspective(principal_id=principal, role=NO_ROLE_RESOLVED),
        recorded_at=determined_at,
        served_at=determined_at,
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
        policy_bindings=(),
    )


class _NoGraphReads:
    """A graph reader with no members: a refusal that read no graph replays without one."""


class _NeverConsulted:
    """An environment whose every member raises: a no-read refusal resolves no plan,
    operator or product (the posture ``tests/products/test_d_impl_344_refusal_reconstruction.py``
    holds ``replay_refusal`` to)."""

    def resolve_plan(self, **_: Any) -> Any:
        raise AssertionError("resolve_plan was reached on a no-read refusal")

    def resolve_composite_plan(self, **_: Any) -> Any:
        raise AssertionError("resolve_composite_plan was reached on a no-read refusal")

    def resolve_operators(self, **_: Any) -> Any:
        raise AssertionError("resolve_operators was reached on a no-read refusal")

    def rehydrate_product(self, **_: Any) -> Any:
        raise AssertionError("rehydrate_product was reached on a refusal")


# =========================================================================
# The hole as worded: another tenant's requested address, through a collision
# =========================================================================


def test_another_tenants_read_refusal_record_answers_a_colliding_principal_as_a_missing_address_does(
    tmp_path: pathlib.Path,
) -> None:
    """``FOREIGN``'s ``ALICE`` is refused a read at the door; ``TENANT``'s ``ALICE``
    — a capability for the recorder's tenant, the same client id, at ``full`` —
    asks for that read-refusal record. It must answer exactly what the same
    address answered while nothing was filed there: the recorded absence,
    ``nonexistent`` / ``evidence-absent``, with nothing of ``FOREIGN``'s ask in it.

    The record's address is known before it exists because the determination
    clock is fixed: a twin door, built identically over its own store, mints
    the same record first.
    """
    twin = _World(tmp_path / "twin")
    address = _record_address(_read(twin, FOREIGN_ALICE, "blob", ASKED))

    world = _World(tmp_path / "door")
    before = _answers(world, OWN_ALICE, address)
    assert _record_address(_read(world, FOREIGN_ALICE, "blob", ASKED)) == address, "the twin door minted another record"
    after = _answers(world, OWN_ALICE, address)

    _assert_identical(before, after)
    for surface in SURFACES:
        assert _internal_cause(world, after[surface]) == ("nonexistent", ERROR_EVIDENCE_ABSENT), surface
        assert ASKED.encode() not in after[surface], surface


def test_a_read_refusal_record_binds_the_tenant_and_principal_the_refused_capability_named(
    tmp_path: pathlib.Path,
) -> None:
    """The mechanism: the record names the tenant the refused capability was
    verified for — ``FOREIGN`` — beside that capability's principal, while the
    door's recorder still files it under its own tenant."""
    world = _World(tmp_path)
    record, internal = _record_at(world, _record_address(_read(world, FOREIGN_ALICE, "blob", ASKED)))

    assert internal.resource is not None
    assert (internal.resource.tenant_id, record.perspective_conditioning.principal_id) == (FOREIGN, ALICE)
    assert record.tenant_id == TENANT


# =========================================================================
# The controls: who still reads a read-refusal record
# =========================================================================


def test_the_refused_principal_of_another_tenant_cannot_read_its_record_back_through_this_door(
    tmp_path: pathlib.Path,
) -> None:
    """Said plainly, because the design does not allow it: ``FOREIGN``'s
    ``ALICE`` cannot read its own read-refusal record through a door whose
    recorder is ``TENANT``'s. The record is decided under ``FOREIGN`` and filed
    under ``TENANT`` — the only tenant this door's recorder can file under — and
    the governed read serves a record only where it is filed under the tenant it
    was decided under (the forged-record provenance check, unchanged). It could
    not read it before the binding either: hold 0 refused it then."""
    world = _World(tmp_path)
    address = _record_address(_read(world, FOREIGN_ALICE, "blob", ASKED))

    for surface in SURFACES:
        assert _internal_cause(world, _read(world, FOREIGN_ALICE, surface, address)) == (
            "nonexistent",
            ERROR_EVIDENCE_ABSENT,
        ), surface


def test_a_principal_of_the_recorders_tenant_still_reads_its_own_read_refusal_record(
    tmp_path: pathlib.Path,
) -> None:
    """``D-IMPL-345`` R-2 (the chain is not permanently dark), on the
    multi-tenant door: ``TENANT``'s ``ALICE`` reads back its own read refusal."""
    world = _World(tmp_path)
    address = _record_address(_read(world, OWN_ALICE, "blob", ASKED))

    assert _read(world, OWN_ALICE, "blob", address) == world.store.get(content_address=address)
    record, internal = _record_at(world, address)
    assert internal.request.parameters == {"reference": ASKED}
    assert internal.resource is not None
    assert (internal.resource.tenant_id, record.perspective_conditioning.principal_id) == (TENANT, ALICE)


# =========================================================================
# The adjacent sweep: hold 3 is a lookup keyed by the principal id
# =========================================================================


def test_hold_three_reads_the_level_in_force_for_the_requesting_tenant_not_the_recorders(
    tmp_path: pathlib.Path,
) -> None:
    """``FOREIGN``'s ``ALICE`` reads its own record — a served record ``FOREIGN``'s
    writer filed — through ``TENANT``'s door. The level that decides whether it
    crosses is the one in force for ``FOREIGN``'s ``ALICE``, never the one
    ``TENANT``'s policy declares for the colliding ``TENANT``'s ``ALICE``, in
    either direction."""
    upgrade = _World(tmp_path / "upgrade", own_level=DISCLOSURE_FULL, foreign_level=DISCLOSURE_MINIMAL)
    own = upgrade.served_record(tenant=FOREIGN, principal=ALICE)
    answer = _read(upgrade, FOREIGN_ALICE, "blob", own)
    assert answer != upgrade.store.get(content_address=own), (
        "the recorder's tenant's level for a colliding principal id disclosed another tenant's record"
    )
    assert _internal_cause(upgrade, answer) == ("unauthorized", ERROR_EVIDENCE_DISCLOSURE_WITHHELD)

    downgrade = _World(tmp_path / "downgrade", own_level=DISCLOSURE_MINIMAL, foreign_level=DISCLOSURE_FULL)
    own = downgrade.served_record(tenant=FOREIGN, principal=ALICE)
    assert _read(downgrade, FOREIGN_ALICE, "blob", own) == downgrade.store.get(content_address=own), (
        "the recorder's tenant's level for a colliding principal id withheld the caller's own record"
    )


def test_a_refusal_of_another_tenants_principal_is_disclosed_at_its_own_level_not_the_recorders(
    tmp_path: pathlib.Path,
) -> None:
    """The third lookup on this path keyed by the principal id: the level the
    door's recorder discloses a refusal SHELL at. ``FOREIGN``'s ``ALICE`` is at
    ``minimal``; the recorder's tenant declares ``full`` for its own ``ALICE``.
    Every refusal ``FOREIGN``'s ``ALICE`` receives is disclosed under ``FOREIGN``'s
    policy at ``FOREIGN``'s level for ``ALICE`` — so a missing address and another
    ``FOREIGN`` principal's genuine record are ONE shell to it, as its own posture
    requires — and, the other way round, at its own ``full``."""
    upgrade = _World(tmp_path / "upgrade", own_level=DISCLOSURE_FULL, foreign_level=DISCLOSURE_MINIMAL)
    nowhere, others = "b" * 64, upgrade.served_record(tenant=FOREIGN, principal=BOB)
    missing = _read(upgrade, FOREIGN_ALICE, "blob", nowhere)
    poached = _read(upgrade, FOREIGN_ALICE, "blob", others)
    for answer in (missing, poached):
        assert _disclosure_decision(upgrade, answer) == (
            DISCLOSURE_MINIMAL,
            product_entitlement_key(tenant_id=FOREIGN),
        ), "a refusal of another tenant's principal was disclosed under the recorder's tenant's level"
    assert _without_the_ask(missing, nowhere) == _without_the_ask(poached, others)

    downgrade = _World(tmp_path / "downgrade", own_level=DISCLOSURE_MINIMAL, foreign_level=DISCLOSURE_FULL)
    assert _disclosure_decision(downgrade, _read(downgrade, FOREIGN_ALICE, "blob", nowhere)) == (
        DISCLOSURE_FULL,
        product_entitlement_key(tenant_id=FOREIGN),
    )


# =========================================================================
# "Check existing records too" — Dave, 2026-10-07 19:31 (Q3): "Old, unmarked
# read-refusal records read as missing for everyone. The marker must have
# trusted provenance; caller-supplied bytes cannot confer trust. Document the
# loss of owner read-back."
# =========================================================================


def test_a_record_written_before_the_marker_is_told_apart_from_one_the_door_writes_today(
    tmp_path: pathlib.Path,
) -> None:
    """Before the marker, the record the door filed for ``FOREIGN``'s ``ALICE``
    asking ``ASKED`` was byte-for-byte the record it files for ``TENANT``'s
    ``ALICE`` asking the same thing at the same instant, so nothing could tell an
    attributed refusal from a legitimate one. The marker can: the record the
    door writes today carries it, and the old one does not."""
    world = _World(tmp_path)
    before_the_marker = _record_address(
        _record_as_written_before_the_binding(world.recorder, principal=ALICE, reference=ASKED)
    )
    today = _record_address(_read(world, OWN_ALICE, "blob", ASKED))

    assert today != before_the_marker, "the door still writes the record it wrote before the marker"
    _, old = _record_at(world, before_the_marker)
    _, new = _record_at(world, today)
    assert old.resource is not None and new.resource is not None
    assert (old.resource.tenant_from, new.resource.tenant_from) == (None, "capability")


def test_a_read_refusal_record_written_before_the_marker_reads_as_missing_for_everyone(
    tmp_path: pathlib.Path,
) -> None:
    """Every reader of an unmarked read-refusal record gets exactly what the
    address answered while nothing was filed there — the owner it names
    (``TENANT``'s ``ALICE``: the loss of owner read-back Dave ruled), another
    principal of the recorder's tenant (who read ``unauthorized`` at hold 1
    before), and another tenant's principal with the owner's client id — with
    the recorded absence behind it and nothing of the ask in it. A twin door
    mints the old record first, so its address is known in advance."""
    twin = _World(tmp_path / "twin")
    address = _record_address(_record_as_written_before_the_binding(twin.recorder, principal=ALICE, reference=ASKED))

    world = _World(tmp_path / "door")
    readers = {"owner": OWN_ALICE, "same-tenant": OWN_BOB, "other-tenant": FOREIGN_ALICE}
    before = {who: _answers(world, grant, address) for who, grant in readers.items()}
    assert _record_address(
        _record_as_written_before_the_binding(world.recorder, principal=ALICE, reference=ASKED)
    ) == address, "the twin door minted another record"

    for who, grant in readers.items():
        after = _answers(world, grant, address)
        _assert_identical(before[who], after)
        for surface in SURFACES:
            assert _internal_cause(world, after[surface]) == ("nonexistent", ERROR_EVIDENCE_ABSENT), (who, surface)
            assert ASKED.encode() not in after[surface], (who, surface)


def _marked_document(tmp_path: pathlib.Path, *, reference: str) -> tuple[str, Any]:
    """A MARKED read-refusal record naming ``TENANT``'s ``ALICE`` and ``reference``, as a document a caller can file.

    Minted by the governed read itself — the marker's only writer — on a
    scratch door built exactly as the door under test is, so the bytes are
    the ones the fabric's record writer would file. A caller holding them can
    file them only on a client lane.
    """
    scratch = _World(tmp_path / "scratch")
    address = _record_address(_read(scratch, OWN_ALICE, "blob", reference))
    _, internal = _record_at(scratch, address)
    assert internal.resource is not None and internal.resource.tenant_from == "capability", (
        "the governed read minted no marker"
    )
    return address, json.loads(scratch.store.get(content_address=address))


@pytest.mark.parametrize(
    "forger_tenant", [FOREIGN, TENANT], ids=["another-tenants-client-lane", "the-tenants-own-client-lane"]
)
def test_a_marked_read_refusal_record_filed_on_a_client_lane_answers_as_a_missing_address_does(
    tmp_path: pathlib.Path, forger_tenant: str
) -> None:
    """Caller-supplied bytes cannot confer trust (Q3). A read-refusal record
    carrying the marker, naming ``TENANT``'s ``ALICE`` and an ask she never
    made, is filed on a client lane — another tenant's, and her own tenant's —
    and ``ALICE`` reads it through the blob and presence resources: each answers
    what it answered while nothing was filed there. The marker counts only on a
    record the provenance check proved the fabric's record writer filed."""
    address, document = _marked_document(tmp_path, reference=FORGED_ASK)

    world = _World(tmp_path / "door")
    before = _answers(world, OWN_ALICE, address)
    filed = world.store.put(
        capability(ArtifactWrite, tenant=forger_tenant, resource=f"{CLIENT_CLASS}/forged-read-refusal"),
        document,
    )
    assert filed.content_address == address
    after = _answers(world, OWN_ALICE, address)

    _assert_identical(before, after)
    for surface in SURFACES:
        assert _internal_cause(world, after[surface]) == ("nonexistent", ERROR_EVIDENCE_ABSENT), surface


def test_a_marked_read_refusal_record_filed_on_a_client_lane_confers_nothing_on_an_in_process_governed_read(
    tmp_path: pathlib.Path,
) -> None:
    """The same forgery handed to the governed read in process, through no
    door: :func:`~ccf_runtime.authz.delivery_boundary.govern_dereference` over
    the store, with a capability for ``TENANT``'s ``ALICE``, answers it exactly
    as it answered the address while nothing was filed there."""
    address, document = _marked_document(tmp_path, reference=FORGED_ASK)
    world = _World(tmp_path / "door")
    consulted = compose_erasure_consult(
        world.store,
        index=no_erasures(),
        audit_log=ControlPlaneRegistry().audit_log,
        clock=lambda: AUDIT_INSTANT,
        control_plane=ControlPlaneRegistry(),
        erasure_trust=declared_erasure_trust(),
    )

    def ask() -> Any:
        return govern_dereference(
            capability(ArtifactRead, tenant=TENANT, resource=address, principal=ALICE),
            reference=DereferenceRequest(reference=address, by_uri=False, wants_bytes=True),
            store=consulted,
            entitlement_source=world.source,
            refusal_recorder=world.recorder,
            audit_log=ControlPlaneRegistry().audit_log,
            surface=SURFACE_MCP_RESOURCE,
            address=artifact_blob_uri(content_address=address),
        )

    before = ask()
    world.store.put(
        capability(ArtifactWrite, tenant=TENANT, resource=f"{CLIENT_CLASS}/forged-read-refusal"), document
    )
    after = ask()

    assert isinstance(after, RefusalEnvelope), "a marked record filed on a client lane was served in process"
    assert canonical_bytes(after) == canonical_bytes(before)
    assert _internal_cause(world, canonical_bytes(after)) == ("nonexistent", ERROR_EVIDENCE_ABSENT)


def test_a_new_read_refusal_record_carries_the_marker_and_still_binds_who_asked(
    tmp_path: pathlib.Path,
) -> None:
    """The governed read writes the marker on every read-refusal record it
    mints, beside the tenant and principal that asked; and the owner of a new,
    marked record still reads it back (``D-IMPL-345`` R-2)."""
    world = _World(tmp_path)
    record, internal = _record_at(world, _record_address(_read(world, FOREIGN_ALICE, "blob", ASKED)))
    assert internal.resource is not None
    assert (
        internal.resource.tenant_from,
        internal.resource.tenant_id,
        record.perspective_conditioning.principal_id,
    ) == ("capability", FOREIGN, ALICE)

    own = _record_address(_read(world, OWN_ALICE, "blob", ASKED))
    assert _read(world, OWN_ALICE, "blob", own) == world.store.get(content_address=own)


def test_read_refusal_records_from_before_and_after_the_binding_replay_to_their_own_addresses(
    tmp_path: pathlib.Path,
) -> None:
    """Replay determinism: a read-refusal record minted as the shipped writer at
    ``7bf069cc`` minted it, and one minted by the door now, each reconstruct
    through :func:`ccf.replay.engine.replay_refusal` at exactly their own
    address; and a served record still resolves to its own address."""
    world = _World(tmp_path)
    legacy = _record_address(_record_as_written_before_the_binding(world.recorder, principal=ALICE, reference=ASKED))
    current = _record_address(_read(world, FOREIGN_ALICE, "blob", "c" * 64))
    _, old = _record_at(world, legacy)
    _, new = _record_at(world, current)
    assert old.resource is not None and new.resource is not None
    assert (old.resource.tenant_from, new.resource.tenant_from) == (None, "capability")

    for address in (legacy, current):
        outcome = replay_refusal(
            record_address=address,
            store=world.store,
            reader=_NoGraphReads(),  # type: ignore[arg-type]
            control_plane=world.registry,
            environment=_NeverConsulted(),
        )
        assert isinstance(outcome, RefusalReplayOutcome), outcome
        assert outcome.record_content_address == address
        assert content_hash(outcome.record) == address
    served = world.served_record(tenant=FOREIGN, principal=ALICE)
    assert content_hash(DecisionReplayRecord.model_validate_json(world.store.get(content_address=served))) == served
