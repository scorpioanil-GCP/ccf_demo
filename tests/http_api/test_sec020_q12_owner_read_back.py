"""SEC-020 channel 3 under Dave's Q12 ruling: owner read-back is default-deny on every path.

Dave, 2026-10-07 19:31 MST, Q12: *"(a) Default-deny owner read-back, with an
explicit tenant class allowlist. Reject withholding classes—including affected
composites—and apply the restriction to existing records and every read/replay
path."*

A Decision Replay record's dimension 1 is the REAL read (``D-IMPL-371``), so the
record behind a withheld answer names what the answer hid; ``D-IMPL-345`` let
its owner at ``full`` read it back. These controls hold the owner's read-back to
default-deny on every path that can deliver a record: the HTTP replay reads by
content address and by URI, the HTTP artifact read, the MCP artifact server's
blob resource, and the MCP Experience door's argument-less ``get_replay_record``.
The owner is entitled to the class and discloses at ``full`` throughout, so a
refusal here is the read-back rule and nothing else; the refusal's mechanism is
asserted by name once the read is refused.

The guard at the end holds the other side: a read-refusal record — the evidence
read's own determination, which carries no product determination and no read of
any subject — still reads back for its owner (Dave's Q3; ``D-IMPL-345`` C20).

Every domain value is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import anyio
import httpx
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from ccf.products.refusal import RefusalEnvelope
from ccf.replay.record import DecisionReplayRecord
from http_api.conftest import call
from tests.http_api.test_sec020_withheld_record_dereference import (
    OWNER_TOKEN,
    PAVED_WITHHELD,
    _ask,
    _door,
    _reference,
)
from tests.mcp.test_c2_tenant_hold_mcp import (
    PRINCIPAL as MCP_PRINCIPAL,
)
from tests.mcp.test_c2_tenant_hold_mcp import (
    TENANT as MCP_TENANT,
)
from tests.mcp.test_c2_tenant_hold_mcp import _file, _read, _record, _world
from tests.products.test_withheld_is_indistinguishable_from_absent import (
    FROM_DECISION,
    FROM_ENTITY_FRESHNESS,
)

import pytest


def _internal_error_code(store: Any, reference: str) -> str:
    """The INTERNAL error code behind a disclosed refusal, read from its own record."""
    address = store.resolve_uri(uri=reference) if reference.startswith("ccf-artifact://") else reference
    record = DecisionReplayRecord.model_validate_json(store.get(content_address=address))
    internal = RefusalEnvelope.model_validate_json(record.content_generation_path.assembly_refusal)
    return str(json.loads(internal.fields["error_code"]))


def _owner_get(door: Any, path: str, **params: str) -> httpx.Response:
    return call(
        door.app,
        "GET",
        path,
        params=params or None,
        headers={"Authorization": f"Bearer {OWNER_TOKEN}"},
    )


@pytest.mark.parametrize("route", ["decisions", "resolutions", "artifact"])
@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_q12_the_owner_cannot_read_back_a_product_record_of_a_class_the_tenant_has_not_listed(
    tmp_path: pathlib.Path, anchor: str, route: str
) -> None:
    """HTTP: the owner, granted the class at ``full``, presents the reference its
    own answer handed it — the record behind a withheld answer — to each evidence
    route. Default-deny: no class is listed, so the record does not cross."""
    with _door(tmp_path, "q12-http", anchor=anchor, holds_subject=True) as door:
        reference = _reference(_ask(door, PAVED_WITHHELD))
        store = door.opened.artifact_store
        address = store.resolve_uri(uri=reference)
        if route == "decisions":
            read = _owner_get(door, "/replay/decisions", content_address=address)
        elif route == "resolutions":
            read = _owner_get(door, "/replay/resolutions", uri=reference)
        else:
            read = _owner_get(door, f"/artifact/{address}")
        assert read.status_code != int(httpx.codes.OK), (
            f"[{anchor}, {route}] the owner read back its own product record"
            f" (status 200) although no class is listed: {read.text[:200]}"
        )
        from ccf_runtime.http_api.errors import ERROR_EVIDENCE_CLASS_SEALED  # noqa: PLC0415

        shell_reference = read.json()["refusal"]["replay_reference"]
        assert _internal_error_code(store, shell_reference) == ERROR_EVIDENCE_CLASS_SEALED


def test_q12_the_owner_cannot_read_back_a_product_record_through_the_mcp_artifact_blob(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MCP artifact server: the owner at ``full`` reads its own record's bytes by
    content address through the blob resource. Default-deny refuses: the
    tenant grants the class at ``full`` and lists nothing for read-back."""
    import tests.mcp.test_c2_tenant_hold_mcp as c2  # noqa: PLC0415

    granted = c2._policy

    def unlisted(tenant: str) -> Any:
        policy = granted(tenant)
        return type(policy).model_validate(
            {**policy.model_dump(), "evidence_readable_classes": frozenset()}
        )

    monkeypatch.setattr(c2, "_policy", unlisted)
    world = _world(tmp_path)
    address = _file(world, _record(tenant=MCP_TENANT, principal=MCP_PRINCIPAL, subject="subject-q12"))
    answer = _read(world, "blob", address)
    assert answer != world.store.get(content_address=address), (
        "the owner read back its own product record's bytes through the MCP"
        " artifact blob resource although no class is listed"
    )
    shell = RefusalEnvelope.model_validate_json(answer)
    from ccf_runtime.http_api.errors import ERROR_EVIDENCE_CLASS_SEALED  # noqa: PLC0415

    assert _internal_error_code(world.recorded, shell.replay_reference) == ERROR_EVIDENCE_CLASS_SEALED


# --- the MCP Experience door's argument-less replay read ---------------------------


def _experience_server(tmp_path: pathlib.Path, *, record_json: str, reads: list[str]) -> Any:
    """The Experience door exposing only ``get_replay_record``, over a seam handing out ``record_json``."""
    from ccf_runtime.mcp.experience import GET_REPLAY_RECORD_TOOL, build_experience_server  # noqa: PLC0415
    from tests.mcp.guarded_servers import (  # noqa: PLC0415
        TENANT,
        _auth,
        _entitlement_world,
        _perspective,
        _verifier,
        authorizer_granting,
    )

    def reader() -> str:
        reads.append("read")
        return record_json

    source, recorder = _entitlement_world(tmp_path)
    return build_experience_server(
        server_name="q12-experience",
        product_resolver=lambda **kw: None,
        replay_record_reader=reader,
        get_replay_record_description="q12 fixture",
        replay_record_tenant=TENANT,
        tool_allowlist=frozenset({GET_REPLAY_RECORD_TOOL}),
        token_verifier=_verifier(),
        auth_settings=_auth(),
        authorizer=authorizer_granting(),
        entitlement_source=source,
        perspective_resolver=_perspective,
        refusal_recorder=recorder,
    )


def _call_replay_tool(server: Any) -> tuple[str | None, BaseException | None]:
    from ccf_runtime.mcp.experience import GET_REPLAY_RECORD_TOOL  # noqa: PLC0415
    from tests.mcp.test_product_roster import TENANTS_CLAIM_WIRE_NAME  # noqa: PLC0415
    from tests.mcp.guarded_servers import PRINCIPAL, SCOPE, TENANT  # noqa: PLC0415

    reset = auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="in-process",
                client_id=PRINCIPAL,
                scopes=[SCOPE],
                claims={TENANTS_CLAIM_WIRE_NAME: [TENANT]},
            )
        )
    )
    try:
        try:
            _, structured = anyio.run(server.call_tool, GET_REPLAY_RECORD_TOOL, {})
        except BaseException as raised:  # noqa: BLE001 — the subject under test
            return None, raised
    finally:
        auth_context_var.reset(reset)
    return str(structured["result"]), None


def test_q12_the_experience_door_does_not_serve_the_record_behind_a_withheld_answer(
    tmp_path: pathlib.Path,
) -> None:
    """MCP Experience door: ``get_replay_record`` hands any verified caller of the
    declared tenant whatever record the deployment's seam returns — here the
    record behind a withheld answer, whose dimension 1 names the acquired
    subject. Q12 requires the read-back rule on every path; this one names no
    address, so no provenance can be shown for what it would serve."""
    with _door(tmp_path, "q12-experience-source", anchor=FROM_DECISION, holds_subject=True) as door:
        reference = _reference(_ask(door, PAVED_WITHHELD))
        store = door.opened.artifact_store
        record_json = store.get(content_address=store.resolve_uri(uri=reference)).decode("utf-8")
    assert PAVED_WITHHELD in record_json, "the case was not constructed: the record does not name the subject"
    reads: list[str] = []
    served, raised = _call_replay_tool(_experience_server(tmp_path, record_json=record_json, reads=reads))
    assert served is None or PAVED_WITHHELD not in served, (
        "the Experience door served the record behind a withheld answer, the"
        " withheld subject named in its dimension 1"
    )
    assert reads == [], "the door read the record before refusing it"
    from ccf_runtime.mcp.experience import ExperienceReplayReadRefused  # noqa: PLC0415

    chain: list[BaseException] = []
    current: BaseException | None = raised
    while current is not None and current not in chain:
        chain.append(current)
        current = current.__cause__ or current.__context__
    assert any(isinstance(link, ExperienceReplayReadRefused) for link in chain), repr(raised)


# --- the guard: a read-refusal record still reads back for its owner -----------------


def test_q12_guard_the_owner_still_reads_back_its_own_read_refusal_record(tmp_path: pathlib.Path) -> None:
    """Q3 / ``D-IMPL-345`` C20, held through Q12: a read-refusal record carries no
    product determination and no read of any subject, so the class allowlist does
    not apply to it — the owner at ``full`` reads its own refusal chain back with
    no class listed."""
    with _door(tmp_path, "q12-guard", anchor=FROM_DECISION, holds_subject=True) as door:
        refused = _owner_get(door, "/replay/decisions", content_address="e" * 64)
        assert refused.status_code != int(httpx.codes.OK), refused.text[:200]
        chain = refused.json()["refusal"]["replay_reference"]
        back = _owner_get(door, "/replay/resolutions", uri=chain)
        assert back.status_code == int(httpx.codes.OK), back.text[:300]
        record = DecisionReplayRecord.model_validate_json(back.content)
        assert record.perspective_conditioning.principal_id == "sec020-owner"


# --- the mechanism (written with the fix) -------------------------------------------


def _paved_open(tmp_path: pathlib.Path, name: str, *, never: bool, project: Any) -> Any:
    """The class-seeded paved road, the source holding the withheld subject."""
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415
    from tests.products.test_withheld_is_indistinguishable_from_absent import (  # noqa: PLC0415
        CLASS_SEEDED,
        _AcquireForSubject,
        _paved_config,
    )

    base = tmp_path / name
    base.mkdir()
    config = _paved_config(anchor=FROM_DECISION, seeding=CLASS_SEEDED)
    if never:
        config["product_class"]["subject_withholding"] = "never"
    root = _write_tree(base, config=config)
    return _open(root, base / "scratch", acquire=_AcquireForSubject(), project=project)


def _question(opened: Any, subject: str) -> Any:
    from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER  # noqa: PLC0415
    from tests.products.test_paved_road import ASKED_AT  # noqa: PLC0415

    return opened.question(
        subject=subject, asked_at=ASKED_AT, intent="fixture-intent",
        freshness="fixture-freshness", parameters={THRESHOLD_PARAMETER: 1000},
    )


def test_q12_a_tenant_listing_a_class_that_may_withhold_is_refused_where_the_resolver_boots(
    tmp_path: pathlib.Path,
) -> None:
    """Dave: "Reject withholding classes." A class that does not affirm ``never``
    — every class, until it says otherwise — listed for read-back is refused with
    the typed error where the resolver is built, before any question is answered."""
    from ccf.products.resolver import WithholdingClassListedReadable  # noqa: PLC0415
    from tests.http_api.test_sec020_withheld_record_dereference import _entitle_owner  # noqa: PLC0415
    from tests.products.test_withheld_is_indistinguishable_from_absent import (  # noqa: PLC0415
        PAVED_ABSENT,
        _paved_withholding_project,
    )

    with _paved_open(tmp_path, "listed-may-withhold", never=False, project=_paved_withholding_project) as opened:
        _entitle_owner(opened, readable=True)
        with pytest.raises(WithholdingClassListedReadable, match="evidence_readable_classes"):
            opened.answer(_question(opened, PAVED_ABSENT))


@pytest.mark.parametrize("composite", [False, True], ids=["plain-class", "composite-class"])
def test_q12_the_boot_check_rejects_every_listed_class_that_may_withhold_composites_included(
    composite: bool,
) -> None:
    """Dave: "including affected composites." The check is per class declaration,
    so a composite (a class declaring ``requires``) listed without the
    affirmation is refused exactly as any class is, and either kind affirming
    ``never`` passes."""
    from ccf.controlplane.artifacts import ProductClassDeclaration  # noqa: PLC0415
    from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: PLC0415
    from ccf.products.contract import ChildRequirement  # noqa: PLC0415
    from ccf.products.entitlement import (  # noqa: PLC0415
        PRODUCT_ENTITLEMENT_POLICY,
        ProductEntitlementGrant,
        ProductEntitlementPolicy,
        product_entitlement_key,
    )
    from ccf.products.resolver import (  # noqa: PLC0415
        WithholdingClassListedReadable,
        _refuse_a_listed_class_that_may_withhold,
    )
    from http_api.composition_authority import register_typed_at_composition  # noqa: PLC0415

    tenant, product_class = "q12-tenant", "fixture.q12-class"
    registry = ControlPlaneRegistry()
    register_typed_at_composition(
        registry,
        product_entitlement_key(tenant_id=tenant),
        ProductEntitlementPolicy(
            tenant_id=tenant,
            policy_version="1.0.0",
            principals={
                "q12-owner": ProductEntitlementGrant(
                    permitted_schema_names=frozenset({product_class}),
                    permitted_roles=frozenset({"q12-role"}),
                )
            },
            evidence_readable_classes=frozenset({product_class}),
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    declaration = ProductClassDeclaration(
        semver="1.0.0",
        schema_name=product_class,
        schema_version="1.0.0",
        ttl_anchor="from_decision",
        assembly_mode="algorithmic",
        max_ttl_key=f"{tenant}/max-ttl",
        required_operator_keys=("policy.principal-subgraph",),
        requires=(
            (ChildRequirement(product_class="fixture.q12-child", required=True, compatible_from="1.0.0"),)
            if composite
            else ()
        ),
    )
    with pytest.raises(WithholdingClassListedReadable):
        _refuse_a_listed_class_that_may_withhold(control_plane=registry, tenant=tenant, declaration=declaration)
    affirmed = declaration.model_copy(update={"subject_withholding": "never"})
    _refuse_a_listed_class_that_may_withhold(control_plane=registry, tenant=tenant, declaration=affirmed)


def test_q12_a_class_that_affirms_never_cannot_withhold_its_subject(tmp_path: pathlib.Path) -> None:
    """The affirmation is enforced: a projection that withholds the subject under a
    class affirming ``never`` is refused as a broken deployment before anything is
    recorded or served; the same class answers a subject it does not withhold."""
    from ccf.products.resolver import NeverWithholdingContradicted  # noqa: PLC0415
    from ccf.replay.serve import ServedProduct  # noqa: PLC0415
    from tests.products.test_withheld_is_indistinguishable_from_absent import (  # noqa: PLC0415
        PAVED_ABSENT,
        _paved_withholding_project,
    )

    with _paved_open(tmp_path, "never-withholds", never=True, project=_paved_withholding_project) as opened:
        with pytest.raises(NeverWithholdingContradicted, match="subject_withholding"):
            opened.answer(_question(opened, PAVED_WITHHELD))
        served = opened.answer(_question(opened, PAVED_ABSENT))
        assert isinstance(served, ServedProduct), served
        assert opened.record_of(served).content_generation_path.subject_withholding == "never"


def test_q12_an_existing_record_without_its_classs_affirmation_stays_sealed_when_the_class_is_listed(
    tmp_path: pathlib.Path,
) -> None:
    """Dave: "apply the restriction to existing records." The tenant lists the class
    and the owner is at ``full``; a record carrying no affirmation — every record
    written before the affirmation existed — is refused, and the same record
    carrying the class's affirmation reads back."""
    world = _world(tmp_path)  # the tenant-hold world: the class granted and listed
    existing = _record(tenant=MCP_TENANT, principal=MCP_PRINCIPAL, subject="subject-existing")
    path = existing.content_generation_path
    unmarked = existing.model_copy(
        update={"content_generation_path": path.model_copy(update={"subject_withholding": "unstated"})}
    )
    affirmed_address = _file(world, existing)
    unmarked_address = _file(world, unmarked)
    assert _read(world, "blob", affirmed_address) == world.store.get(content_address=affirmed_address), (
        "the control: a listed class's record carrying the affirmation reads back"
    )
    answer = _read(world, "blob", unmarked_address)
    assert answer != world.store.get(content_address=unmarked_address), (
        "a record without its class's affirmation was read back by its owner"
    )
    shell = RefusalEnvelope.model_validate_json(answer)
    from ccf_runtime.http_api.errors import ERROR_EVIDENCE_CLASS_SEALED  # noqa: PLC0415

    assert _internal_error_code(world.recorded, shell.replay_reference) == ERROR_EVIDENCE_CLASS_SEALED


@pytest.mark.parametrize("touched", [False, True], ids=["read-nothing", "claims-no-read-names-a-touched-entity"])
def test_q12_a_record_that_read_nothing_needs_only_the_listing(tmp_path: pathlib.Path, touched: bool) -> None:
    """Hold 2b's other arm. A record whose dimension 1 is exactly the claim *nothing
    was read* — a refusal made before any read — names no subject an answer could
    have hidden, so with its class listed it reads back without the affirmation.
    A dimension 1 that claims no read while naming a touched entity is not read
    as having read nothing: it stays sealed."""
    from ccf.replay.record import NO_FABRIC_READ, ContextFabricSnapshot  # noqa: PLC0415
    from ccf_runtime.http_api.errors import ERROR_EVIDENCE_CLASS_SEALED  # noqa: PLC0415

    world = _world(tmp_path)  # the class granted at `full` and listed
    base = _record(tenant=MCP_TENANT, principal=MCP_PRINCIPAL, subject="subject-unread")
    dimension_1 = base.context_fabric_snapshot
    snapshot = (
        ContextFabricSnapshot.build(
            tenant_id=dimension_1.tenant_id,
            temporal_boundary=dimension_1.temporal_boundary,
            store_watermark=NO_FABRIC_READ,
            touched_entities=("entity-touched",),
            touched_relationships=(),
        )
        if touched
        else ContextFabricSnapshot.unread(
            tenant_id=dimension_1.tenant_id, temporal_boundary=dimension_1.temporal_boundary
        )
    )
    record = base.model_copy(
        update={
            "context_fabric_snapshot": snapshot,
            "content_generation_path": base.content_generation_path.model_copy(
                update={"subject_withholding": "unstated"}
            ),
        }
    )
    address = _file(world, record)
    answer = _read(world, "blob", address)
    if not touched:
        assert answer == world.store.get(content_address=address), (
            "a listed class's record that read nothing was not read back by its owner"
        )
        return
    assert answer != world.store.get(content_address=address), (
        "a record claiming no read while naming a touched entity was read back"
        " without its class's affirmation"
    )
    shell = RefusalEnvelope.model_validate_json(answer)
    assert _internal_error_code(world.recorded, shell.replay_reference) == ERROR_EVIDENCE_CLASS_SEALED
