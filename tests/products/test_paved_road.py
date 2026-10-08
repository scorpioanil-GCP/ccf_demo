"""The paved road, proven through its public surface (`D-IMPL-343`).

CLAUDE.md §9, §10, §11; the ruling of record is `D-IMPL-343` and its design
(``docs/D-IMPL-343-DESIGN.md`` §5, §11, §12). Every test here drives
:func:`ccf.products.product.open_product` and :func:`ccf_runtime.mcp
.product_door.open_door` from the outside, over a fixture deployment written
in the single-file form with the three paved sections, and never inspects
that a helper exists. The sabotages named in the design's §12 that can be
run without an estate are here; the ones that need the live estate and a
second process are `tests/examples/test_cp_03_canonical_*`.

What is held, exactly:

1. A governed product is served with a record, from ONE store, and two
   questions under one scratch mint two substrate files.
2. The acquisition seam receives the EFFECTIVE request (a class default the
   caller omitted is present), and a refused question acquires nothing.
3. A foreign envelope — another tenant, another instant — is refused by name.
4. The low road is reachable from the paved surface: `build_arguments` + the
   builder yield the SAME content address as `answer`.
5. Every open-time refusal names its section or key; the TTL and
   decision-instant keywords are held equal to the declaration.
6. The standard door composes over the ONE registry and the ONE recorder; a
   wrong lane is refused `class-mismatch` as data with a record; a wrong
   tenant is a broken deployment.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator
from urllib.parse import urlparse
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.fastmcp import FastMCP

from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_config_and_boot
from ccf.deployment.environment import EnvironmentMissing
from ccf.halflife.assessment import DebtFactors
from ccf.halflife.debt import DebtAssessment, assess_debt
from ccf.products.entitlement import ProductEntitlementPolicy, product_entitlement_key
from ccf.products.product import AcquisitionContext, AssessmentContext, OpenedProduct, open_product
from ccf.products.provenance import EffectiveRequest
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.products.resolver import ProductNotResolvable, build_governed_resolver
from ccf.projection.plan import Perspective
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope
from ccf_runtime.mcp.product_door import open_door
from ccf_runtime.mcp.tenancy import ambient_stdio_identity

from tests.products.paved_fixture import granted_control_plane
from tests.deployment.conftest import write_artifact
from tests.deployment.test_replay_binding import (
    ENTITY_CLASS,
    OBSERVED_AT,
    PRINCIPAL,
    PRODUCT_CLASS,
    PRODUCT_VERSION,
    ROLE,
    TENANT,
    THRESHOLD_PARAMETER,
    _plan_factory,
    _servable_config,
)
from tests.composition import declare_wide_temporal_boundary, declared_erasure_trust

ASKED_AT = datetime(2026, 3, 2, 12, 0, tzinfo=UTC)
LIMIT_PARAMETER = "limit"
LIMIT_DEFAULT = 5
DSN_VARIABLE = "PAVED_FIXTURE_DSN"


def _config(**overrides: Any) -> dict[str, Any]:
    """The servable fixture config plus the three paved sections and a class default."""
    document = _servable_config(
        replay={"record_class": "ccf.replay-record", "query_pin_class": "ccf.graph-query", "store_dirname": "artifact-store"},
        ttl={"max_ttl_seconds": 3600, "product_ttl_seconds": 600},
        door={
            "producer_id": "paved-fixture-egress",
            "producer_tenant": TENANT,
            "tool_description": "asks the paved fixture product a question",
            "required_scope": "ccf:egress",
        },
    )
    # A parameter with a CLASS DEFAULT, so the seam test can tell an effective
    # request from a raw one: the caller omits it and the seam must see it.
    document["request_contract"]["arguments"]["properties"][LIMIT_PARAMETER] = {
        "type": "integer",
        "description": "Fixture parameter with a class default.",
    }
    document["request_contract"]["defaults"] = {LIMIT_PARAMETER: LIMIT_DEFAULT}
    document.update(overrides)
    return document


def _environment_text(*, sources: bool = True, door: bool = True) -> str:
    lines = [
        "config: ccf_config.yaml",
        "substrate: {setting: database_path, prefix: paved_fixture, suffix: .sqlite3}",
    ]
    if sources:
        lines += [
            "sources:",
            "  store:",
            f"    dsn: {{from_env: {DSN_VARIABLE}, remedy: 'export {DSN_VARIABLE} with the fixture DSN'}}",
        ]
    if door:
        lines += [
            "door:",
            "  credential: {from_env: PAVED_FIXTURE_TOKEN, remedy: 'set or leave unset'}",
            "  issuer_url: {from_env: PAVED_FIXTURE_ISSUER, remedy: 'export the issuer'}",
            "  resource_server_url: {from_env: PAVED_FIXTURE_RESOURCE, remedy: 'export the resource server'}",
        ]
    return "\n".join(lines) + "\n"


def _write_tree(tmp_path: pathlib.Path, *, config: dict[str, Any] | None = None, environment: str | None = None) -> pathlib.Path:
    root = tmp_path / "deployment"
    root.mkdir(parents=True)
    write_artifact(root, "ccf_config.yaml", config if config is not None else _config())
    (root / "ccf_environment.yaml").write_text(environment if environment is not None else _environment_text(), encoding="utf-8")
    return root


class _Acquire:
    """A spy acquisition: records what it was handed, emits what it is told to."""

    def __init__(self, *, tenant: str | None = None, instant_offset: timedelta = timedelta(0)) -> None:
        self.contexts: list[AcquisitionContext] = []
        self._tenant = tenant
        self._offset = instant_offset

    def __call__(self, context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
        self.contexts.append(context)
        return (
            SignalEnvelope.model_validate(
                {
                    "tenant_id": self._tenant or context.tenant_id,
                    "envelope_id": "envelope-paved-1",
                    "source": {"system_id": "fixture-system"},
                    "ingestion_timestamp": context.instant + self._offset,
                    "observed_time": OBSERVED_AT,
                    "raw_payload": {"account_ref": "acct-1", "classification": "fixture-open", "label": "fixture account"},
                }
            ),
        )


def _assess(context: AssessmentContext) -> DebtAssessment:
    assert context.profile is not None
    return assess_debt(
        DebtFactors(freshness=Decimal(1), completeness=Decimal(1), semantic_consistency=Decimal(1)),
        profile=context.profile,
    )


def _open(root: pathlib.Path, scratch: pathlib.Path, *, acquire: _Acquire | None = None, **overrides: Any) -> OpenedProduct:
    arguments: dict[str, Any] = {
        "config_root": root,
        "scratch": scratch,
        "acquire": acquire or _Acquire(),
        "project": _plan_factory,
        "assess": _assess,
        "environ": {DSN_VARIABLE: "postgresql://fixture", "PAVED_FIXTURE_TOKEN": "fixture-token"},
        "clock": lambda: ASKED_AT + timedelta(minutes=7),
        # SEC-009 (fix round 5): the deployment's erasure trust root — the
        # declared test authority for the paved tenant.
        "erasure_trust": declared_erasure_trust(TENANT),
    }
    arguments.update(overrides)
    if "control_plane" not in arguments:
        # The declared skills are granted through the ledger by an authorized
        # principal BEFORE opening: the paved road requests no grant (D-IMPL-354).
        arguments["control_plane"] = granted_control_plane(root)
    return open_product(**arguments)


def _question(opened: OpenedProduct, **parameters: Any) -> ProductRequest:
    return opened.question(
        subject="acct-1", asked_at=ASKED_AT, intent="fixture-intent", freshness="fixture-freshness",
        parameters={THRESHOLD_PARAMETER: 1000, **parameters},
    )


@pytest.fixture()
def tree(tmp_path: pathlib.Path) -> Iterator[tuple[pathlib.Path, pathlib.Path]]:
    scratch = tmp_path / "scratch"
    yield _write_tree(tmp_path), scratch


# --- 1. served, recorded, per-question -----------------------------------------------


def test_the_paved_road_serves_a_governed_product_with_its_record_from_one_store(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    root, scratch = tree
    with _open(root, scratch) as opened:
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct), served
        assert served.product.schema_name == PRODUCT_CLASS and served.product.tenant_id == TENANT
        record = opened.record_of(served)
        assert record.content_generation_path.product_content_address == content_hash(served.product)
        again = opened.answer(_question(opened))
        assert isinstance(again, ServedProduct)
        assert content_hash(again.product) == content_hash(served.product)
        minted = sorted(scratch.glob("paved_fixture_*.sqlite3"))
        assert len(minted) == 2 and minted[0] != minted[1], "one fresh fabric per question"
        assert (scratch / "artifact-store").is_dir(), "the declared store_dirname under scratch"
        # A refusal is recorded in the SAME store, readable through the same call.
        refused = opened.answer(_question(opened, no_such_parameter=1))
        assert isinstance(refused, RefusalEnvelope)
        assert opened.record_of(refused).content_generation_path.request is not None


# --- 2. the seam receives the effective request; a refused question acquires nothing ---


def test_the_acquisition_seam_receives_the_effective_request_once(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    root, scratch = tree
    spy = _Acquire()
    with _open(root, scratch, acquire=spy) as opened:
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct), served
        record = opened.record_of(served)
    assert len(spy.contexts) == 1, "acquired exactly once per question"
    context = spy.contexts[0]
    assert context.request.parameters[LIMIT_PARAMETER] == LIMIT_DEFAULT, "the class default the caller omitted"
    assert context.request.parameters[THRESHOLD_PARAMETER] == Decimal(1000)
    assert context.tenant_id == TENANT and context.instant == ASKED_AT
    assert context.sources == {"store": {"dsn": "postgresql://fixture"}}
    assert context.perspective.principal_id == PRINCIPAL and context.perspective.role == ROLE
    resolution = EffectiveRequest.model_validate_json(record.policy_bindings.request_resolution)
    assert dict(resolution.values())[LIMIT_PARAMETER] == LIMIT_DEFAULT, "the record and the seam agree"


def test_a_refused_question_acquires_nothing(tree: tuple[pathlib.Path, pathlib.Path]) -> None:
    root, scratch = tree
    spy = _Acquire()
    with _open(root, scratch, acquire=spy) as opened:
        refused = opened.answer(opened.question(subject="acct-1", asked_at=ASKED_AT, intent="i", freshness="f", parameters={}))
    assert isinstance(refused, RefusalEnvelope) and refused.reason == "missing-required-parameter"
    assert spy.contexts == [], "no acquisition ran for a refused request"


# --- 3. the boundary refuses a foreign envelope by name -------------------------------


@pytest.mark.parametrize(
    ("acquire", "named"),
    [
        (_Acquire(tenant="somebody-else"), "tenant"),
        (_Acquire(instant_offset=timedelta(days=1)), "asked as of"),
    ],
    ids=["another-tenant", "another-instant"],
)
def test_a_foreign_envelope_is_refused_by_name(
    tree: tuple[pathlib.Path, pathlib.Path], acquire: _Acquire, named: str
) -> None:
    root, scratch = tree
    with _open(root, scratch, acquire=acquire) as opened, pytest.raises(ValueError, match=named):
        opened.answer(_question(opened))


# --- 4. the low road, reached from the paved surface ------------------------------------


def test_the_low_road_yields_the_same_content_address_through_build_arguments(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    root, scratch = tree
    with _open(root, scratch) as opened:
        paved = opened.answer(_question(opened))
        assert isinstance(paved, ServedProduct)
        # SEC-020 Q9 (`D-IMPL-378`): a hand-composed fabric an acquisition seam
        # writes into is booted for its one question, as the paved road boots its own.
        fabric = load_config_and_boot(
            opened.config_path, registry=opened.control_plane,
            connection={"database_path": str(scratch / "low-road.sqlite3")},
            for_question=True,
        )
        # `D-IMPL-358` step 5 ruling 11: a deployment declaring no temporal boundary
        # refuses every question, so a fixture that means to serve declares one.
        declare_wide_temporal_boundary(opened.control_plane, tenant_id=fabric.tenant_id)
        try:
            arguments = opened.build_arguments(fabric)
            assert "max_ttl_seconds" not in arguments and "decision_instant_parameter" not in arguments
            low = build_governed_resolver(**arguments)(
                tenant=TENANT, product_class=PRODUCT_CLASS, version=PRODUCT_VERSION,
                perspective=opened.default_perspective, request=_question(opened),
            )
        finally:
            fabric.handle.close()
        assert isinstance(low, ServedProduct)
        assert content_hash(low.product) == content_hash(paved.product)
        # Sabotage: one keyword changed, the address moves — the mapping is load-bearing.
        # SEC-020 Q9 (`D-IMPL-378`): a hand-composed fabric an acquisition seam
        # writes into is booted for its one question, as the paved road boots its own.
        fabric = load_config_and_boot(
            opened.config_path, registry=opened.control_plane,
            connection={"database_path": str(scratch / "low-road-2.sqlite3")},
            for_question=True,
        )
        # `D-IMPL-358` step 5 ruling 11: a deployment declaring no temporal boundary
        # refuses every question, so a fixture that means to serve declares one.
        declare_wide_temporal_boundary(opened.control_plane, tenant_id=fabric.tenant_id)
        try:
            arguments = opened.build_arguments(fabric)
            arguments["plan_factory"] = lambda *, required, request: _plan_factory(
                required=required, request=request.model_copy(update={"parameters": {THRESHOLD_PARAMETER: 1}})
            )
            moved = build_governed_resolver(**arguments)(
                tenant=TENANT, product_class=PRODUCT_CLASS, version=PRODUCT_VERSION,
                perspective=opened.default_perspective, request=_question(opened),
            )
        finally:
            fabric.handle.close()
        assert isinstance(moved, ServedProduct) and content_hash(moved.product) != content_hash(paved.product)


# --- 5. open-time refusals, by name --------------------------------------------------------


def test_a_missing_replay_or_ttl_section_is_refused_at_open_by_name(tmp_path: pathlib.Path) -> None:
    for section in ("replay", "ttl"):
        config = _config()
        del config[section]
        root = _write_tree(tmp_path / section, config=config)
        with pytest.raises(ValueError, match=f"'{section}'"):
            _open(root, tmp_path / section / "scratch")


def test_the_declared_gate_and_the_supplied_predicate_are_both_or_neither(tmp_path: pathlib.Path) -> None:
    root = _write_tree(tmp_path / "a")
    with pytest.raises(ValueError, match="declares none"):
        _open(root, tmp_path / "a" / "scratch", gate=lambda *, candidate, evidence=None: None)
    config = _config()
    config["product_class"]["declared_product_gate"] = {"gate_id": "fixture.gate", "gate_version": "1.0.0"}
    root = _write_tree(tmp_path / "b", config=config)
    with pytest.raises(ValueError, match="fixture.gate"):
        _open(root, tmp_path / "b" / "scratch")


def test_scratch_inside_the_config_root_is_refused(tree: tuple[pathlib.Path, pathlib.Path]) -> None:
    root, _ = tree
    with pytest.raises(ValueError, match="inside the config root"):
        _open(root, root / "scratch")


def test_an_unset_source_variable_is_refused_at_open_with_the_remedy(tree: tuple[pathlib.Path, pathlib.Path]) -> None:
    root, scratch = tree
    with pytest.raises(EnvironmentMissing, match=f"export {DSN_VARIABLE}"):
        _open(root, scratch, environ={})


def test_a_composite_without_a_child_resolver_is_refused_at_open(tmp_path: pathlib.Path) -> None:
    config = _config()
    config["product_class"]["requires"] = [{"product_class": "fixture.child", "required": True, "compatible_from": "1.0.0"}]
    root = _write_tree(tmp_path, config=config)
    with pytest.raises(ValueError, match="children="):
        _open(root, tmp_path / "scratch")


def test_the_ttl_and_decision_instant_keywords_are_held_equal_to_the_declaration(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    root, scratch = tree
    with _open(root, scratch) as opened:
        fabric = load_config_and_boot(
            opened.config_path, registry=opened.control_plane,
            connection={"database_path": str(scratch / "equal.sqlite3")},
        )
        # `D-IMPL-358` step 5 ruling 11: a deployment declaring no temporal boundary
        # refuses every question, so a fixture that means to serve declares one.
        declare_wide_temporal_boundary(opened.control_plane, tenant_id=fabric.tenant_id)
        try:
            arguments = opened.build_arguments(fabric)
            build_governed_resolver(**arguments, max_ttl_seconds=3600, product_ttl_seconds=600)  # equal: builds
            with pytest.raises(TypeError, match="product_ttl_seconds=601"):
                build_governed_resolver(**arguments, product_ttl_seconds=601)
            # A class declaring NO decision instant still admits the keyword —
            # the posture every earlier caller had; equality is held only
            # against a declaration (the test below).
            build_governed_resolver(**{**arguments, "decision_instant_parameter": THRESHOLD_PARAMETER})
        finally:
            fabric.handle.close()


def test_a_config_with_a_declared_decision_instant_is_built_from_the_declaration(tmp_path: pathlib.Path) -> None:
    config = _config()
    config["product_class"]["decision_instant_parameter"] = "as_of"
    config["request_contract"]["arguments"]["properties"]["as_of"] = {"type": "string", "description": "the decision instant"}
    root = _write_tree(tmp_path, config=config)
    decided = ASKED_AT + timedelta(minutes=5)
    with _open(root, tmp_path / "scratch") as opened:
        served = opened.answer(_question(opened, as_of=decided.isoformat()))
        assert isinstance(served, ServedProduct), served
        assert served.product.expires_at == decided + timedelta(seconds=600), "the expiry runs from the declared instant"
        assert served.product.temporal_boundary == ASKED_AT
        # R-3b: a builder keyword naming ANOTHER parameter than the declaration is refused with both named.
        fabric = load_config_and_boot(
            opened.config_path, registry=opened.control_plane,
            connection={"database_path": str(tmp_path / "scratch" / "instant.sqlite3")},
        )
        # `D-IMPL-358` step 5 ruling 11: a deployment declaring no temporal boundary
        # refuses every question, so a fixture that means to serve declares one.
        declare_wide_temporal_boundary(opened.control_plane, tenant_id=fabric.tenant_id)
        try:
            with pytest.raises(TypeError, match="decision_instant_parameter: as_of"):
                build_governed_resolver(**{**opened.build_arguments(fabric), "decision_instant_parameter": THRESHOLD_PARAMETER})
        finally:
            fabric.handle.close()


# --- 6. the standard door --------------------------------------------------------------------


def test_open_door_composes_over_the_one_registry_and_refuses_a_wrong_lane_as_data(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    root, scratch = tree
    with _open(root, scratch) as opened:
        door = open_door(opened, environ={"PAVED_FIXTURE_TOKEN": "fixture-token"})
        assert door.credential == "fixture-token" and door.principal_id == PRINCIPAL and door.role == ROLE
        assert door.producer_id == "paved-fixture-egress" and door.tenant_id == TENANT
        _version, policy = opened.control_plane.resolve_latest(product_entitlement_key(tenant_id=TENANT))
        assert isinstance(policy, ProductEntitlementPolicy)
        assert set(policy.principals) == {PRINCIPAL}
        server = door.server(issuer_url="https://issuer.example", resource_server_url="https://door.example/mcp")
        assert server is not None
        # Opening the door twice registers identical content: idempotent, not a conflict.
        open_door(opened, environ={"PAVED_FIXTURE_TOKEN": "fixture-token"})

        wrong_lane = opened.resolve(
            tenant=TENANT, product_class=PRODUCT_CLASS, version="9.9.9",
            perspective=opened.default_perspective, request=_question(opened),
        )
        assert isinstance(wrong_lane, RefusalEnvelope)
        assert wrong_lane.reason == "class-mismatch" and wrong_lane.key == "schema_version"
        assert opened.record_of(wrong_lane) is not None, "recorded in the ONE store"
        with pytest.raises(ProductNotResolvable):
            opened.resolve(
                tenant="another-tenant", product_class=PRODUCT_CLASS, version=PRODUCT_VERSION,
                perspective=opened.default_perspective, request=_question(opened),
            )
        with pytest.raises(ProductNotResolvable):
            opened.resolve(
                tenant=TENANT, product_class=PRODUCT_CLASS, version=PRODUCT_VERSION,
                perspective=opened.default_perspective, request=None,
            )
        served = opened.resolve(
            tenant=TENANT, product_class=PRODUCT_CLASS, version=PRODUCT_VERSION,
            perspective=Perspective(principal_id=PRINCIPAL, role=ROLE), request=_question(opened),
        )
        assert isinstance(served, ServedProduct)


def test_open_door_refuses_a_product_with_no_door_section_or_no_door_names(tmp_path: pathlib.Path) -> None:
    config = _config()
    del config["door"]
    root = _write_tree(tmp_path / "no-section", config=config)
    with _open(root, tmp_path / "no-section" / "scratch") as opened, pytest.raises(ValueError, match="'door' section"):
        open_door(opened, environ={})
    root = _write_tree(tmp_path / "no-names", environment=_environment_text(door=False))
    with _open(root, tmp_path / "no-names" / "scratch") as opened, pytest.raises(ValueError, match="names no 'door'"):
        open_door(opened, environ={})


def test_the_stdio_door_reads_neither_door_url_and_advertises_only_reserved_addresses(
    tree: tuple[pathlib.Path, pathlib.Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """C2-A (b) (``D-IMPL-378``; Dave, 2026-10-08): stdio no longer requires the two URLs.

    Rewritten under the ruling, not deleted (``D-IMPL-235`` (4)). It asserted
    the superseded behavior — ``serve_stdio`` refusing with ``EnvironmentMissing``
    when the issuer variable was unset. Both are advertising for an HTTP app, and
    stdio builds none, so the stdio transport now supplies its own values, as the
    loopback transport derives its own. Those values must be under the reserved
    ``.invalid`` domain, which can never resolve, so nothing they could name is
    reachable (``SECURITY-REVIEW-C2A.md`` R2). ``FastMCP.run`` is stubbed: what is
    observed is the server the door hands its transport, with both variables unset.
    """
    root, scratch = tree
    started: list[tuple[str, str, str]] = []

    def _run(self: FastMCP, transport: str = "stdio", **_: object) -> None:
        assert self.settings.auth is not None
        started.append(
            (transport, str(self.settings.auth.issuer_url), str(self.settings.auth.resource_server_url))
        )

    monkeypatch.setattr(FastMCP, "run", _run)
    with _open(root, scratch) as opened:
        door = open_door(opened, environ={})
        assert door.credential, "minted per boot when the variable is unset"
        door.serve_stdio(
            identity=AuthenticatedUser(
                ambient_stdio_identity(
                    credential=door.credential,
                    principal_id=door.principal_id,
                    scope=door.scope,
                    tenant=door.tenant_id,
                )
            )
        )
    assert [transport for transport, _, _ in started] == ["stdio"], started
    (_, issuer, resource), = started
    for advertised in (issuer, resource):
        host = urlparse(advertised).hostname
        assert host is not None and host.endswith(".invalid"), advertised


def test_the_facade_holds_no_fabric_between_questions_and_boots_nothing_at_open(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    root, scratch = tree
    with _open(root, scratch) as opened:
        assert sorted(scratch.glob("paved_fixture_*.sqlite3")) == []
        assert isinstance(opened.control_plane, ControlPlaneRegistry)
        # `keys` are the strings the Control Plane holds: the bare `replay:` section
        # key placed under the deployment's tenant (D-IMPL-354).
        assert opened.keys.replay == f"{opened.tenant_id}/replay" and opened.ttl.product_ttl_seconds == 600
