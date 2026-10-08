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
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
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
from ccf_runtime.authz.delivery_boundary import DEREFERENCE_PRODUCT_ID, SURFACE_MCP_RESOURCE
from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource
from ccf_runtime.http_api.errors import ERROR_EVIDENCE_ABSENT, ERROR_EVIDENCE_DISCLOSURE_WITHHELD
from ccf_runtime.mcp.artifact_server import artifact_blob_uri, artifact_meta_uri, build_artifact_server
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource, TokenGrant
from tests.composition import declared_erasure_trust, no_erasures
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

#: The address ``FOREIGN``'s principal asks about. Nothing is ever stored there:
#: the answer is a read refusal, and this string is what that record must not
#: carry to anyone else.
ASKED = "a" * 64

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


def _record_as_written_before_the_binding(recorder: ReplayRefusalRecorder, *, principal: str, reference: str) -> RefusalEnvelope:
    """A read refusal of ``reference`` for ``principal``, minted exactly as the shipped writer at ``7bf069cc`` minted it.

    Not a hand-edited record: the same two seams ``govern_dereference``'s
    ``refuse`` called at ``7bf069cc`` for an absence — ``envelope_for`` over the
    ``nonexistent`` / ``evidence-absent`` determination, then the door's own
    ``recorder.record`` — with the one value that writer chose and the binding
    changes: the resource identity's ``tenant_id`` was the RECORDER's tenant,
    whichever tenant the refused capability named. Called for a principal of
    another tenant, this is that principal's read-refusal record as the door
    filed it before the binding — and, for the recorder's own tenant's
    principal, it is byte-for-byte the record the door writes today
    (:func:`test_a_record_written_before_the_binding_is_byte_for_byte_one_the_door_writes_today`).
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
            surface=SURFACE_MCP_RESOURCE,
            address=artifact_blob_uri(content_address=reference),
            tenant_id=recorder.tenant_id,
            determined_at=AUDIT_INSTANT,
        ),
        policy_bindings=(),
    )
    return recorder.record(
        envelope,
        perspective=Perspective(principal_id=principal, role=NO_ROLE_RESOLVED),
        recorded_at=AUDIT_INSTANT,
        served_at=AUDIT_INSTANT,
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
# "Check existing records too"
# =========================================================================


def test_a_record_written_before_the_binding_is_byte_for_byte_one_the_door_writes_today(
    tmp_path: pathlib.Path,
) -> None:
    """Why the next case is a proposal and not a fix. The record the door filed,
    before the binding, for ``FOREIGN``'s ``ALICE`` asking ``ASKED`` is
    byte-for-byte — one content address — the record the door files today for
    ``TENANT``'s ``ALICE`` asking ``ASKED`` at the same instant: both name the
    recorder's tenant and the same principal, reference, surface and instant.
    ``D-IMPL-345`` R-2 keeps the second readable by ``TENANT``'s ``ALICE``, so no
    rule over a record's content can refuse the first to the same caller."""
    world = _World(tmp_path)
    before_the_binding = _record_address(
        _record_as_written_before_the_binding(world.recorder, principal=ALICE, reference=ASKED)
    )

    assert _record_address(_read(world, OWN_ALICE, "blob", ASKED)) == before_the_binding


@pytest.mark.xfail(
    strict=True,
    reason=(
        "OPEN, a proposal for Dave (D-IMPL-378 lane 378-refusal): a read-refusal record written before the"
        " binding names the recorder's tenant, and is byte-for-byte the record the binding writes for the"
        " recorder's own principal asking the same thing at the same instant — so no rule over its content"
        " can refuse one and serve the other. Failing it closed needs a positive marker on new records"
        " (a replay-record content change) or no read-refusal record readable at all (reverses D-IMPL-345"
        " R-2); either is Dave's to rule"
    ),
)
def test_a_read_refusal_record_written_before_the_binding_is_not_readable_by_a_colliding_principal(
    tmp_path: pathlib.Path,
) -> None:
    world = _World(tmp_path)
    address = _record_address(_record_as_written_before_the_binding(world.recorder, principal=ALICE, reference=ASKED))

    for surface in SURFACES:
        answer = _read(world, OWN_ALICE, surface, address)
        assert ASKED.encode() not in answer, surface
        assert _internal_cause(world, answer) == ("nonexistent", ERROR_EVIDENCE_ABSENT), surface


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
