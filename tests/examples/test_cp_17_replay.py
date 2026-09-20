"""Replay, invalidation and non-disclosure on the record — `MWE-G11`, `MWE-G17`, `MWE-G19`.

`examples/cp-17-mnpi-wall-enforcement` on the paved producer road
(`CP-SPEC-017`). Three properties of what the tree RECORDS rather than of what
it serves: that each principal's product rebuilds byte for byte from its own
record and the ungranted principal's refusal reconstructs with its cause
(`MWE-G17`); that the Reg FD boundary, once in the invalidation register,
refuses a determination whose snapshot precedes it and no other (`MWE-G11`);
and that neither a served vessel nor its replay record carries a wall-decision
input the principal is not entitled to, while the record still replays
(`MWE-G19`).

A fourth test claims no gate: it replays a computed-empty serve and is an
expected failure recording an SDK gap (`CP17-F-08`), kept executable so the
gap is measured on every run rather than remembered.

**Reads the estate, seeds nothing** (CLAUDE.md §9). Nothing here pins an
estate count or a date: the instants come off `artifacts/question.yaml`, the
Reg FD boundary off the served issuer member, the issuer's L2 URI off the
reopened view, and every assertion is a relationship between two things this
module computed.
"""

from __future__ import annotations

import os
import pathlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import yaml

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.invalidation import ControlPlaneInvalidationSink
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.products.product import OpenedProduct
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf.replay.engine import (
    RefusalReplayOutcome,
    ReplayDivergence,
    ReplayOutcome,
    ReplayRecordKindMismatch,
    ReplayUnresolvable,
    replay,
    replay_refusal,
)
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-17-mnpi-wall-enforcement"

ESTATE_VARIABLES = (
    "CCF_CP_17_SQLITE_PATH",
    "CCF_CP_17_POSTGRES_DSN", "CCF_CP_17_POSTGRES_SCHEMA",
    "CCF_CP_17_FLUREE_URL", "CCF_CP_17_FLUREE_LEDGER",
    "CCF_CP_17_MONGO_URI", "CCF_CP_17_MONGO_DB",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")

CONFIG: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
ENVIRONMENT: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_environment.yaml").read_text(encoding="utf-8"))
QUESTION: dict[str, Any] = yaml.safe_load((EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
INSTANTS: dict[str, datetime] = {name: datetime.fromisoformat(value) for name, value in QUESTION["instants"].items()}

#: The demonstration issuer (SP Plus) is the artifact's subject; the freshness
#: comparison issuer named here (American Healthcare REIT) is the OTHER issuer
#: the invalidation gate must leave alone; the last is a LEI no estate holds.
SUBJECT: str = QUESTION["question"]["subject"]
OTHER_ISSUER = "2549004GGE2APGNT6O92"
NOBODY = "0000000000000000NOPE"

#: The four principals the estate registers; their roles are read off the
#: estate's own principal table, never restated here.
BANKER: str = CONFIG["default_perspective"]["principal_id"]
ANALYST = "PRIN-RES-002"
TRADER = "PRIN-TRD-003"
KYC = "PRIN-KYC-004"
ENTITLED = (BANKER, ANALYST, TRADER)

#: The wall-decision inputs no served principal is entitled to: the crossing
#: that keyed the banker's wall, and the control room's restriction row.
WALL_INPUTS = ("WALL-000", "research-restricted", "RC-DEAL")
INVALIDATION_REASON = "reg-fd-disclosure"
GATE_DEPENDENCY_INVALIDATION = "dependency-invalidation"
DIAGNOSTIC_TOLERANCE = "1.0"


# --- fixtures and helpers -----------------------------------------------------------


@pytest.fixture(scope="module")
def estate() -> None:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [n for n in ESTATE_VARIABLES if not os.environ.get(n)]
    if missing:
        message = (
            f"the curated estate is not configured: {', '.join(missing)} unset."
            " Point them at the v2 namespaces — Fluree `fibo-v2`, PostgreSQL `ccf_v2`, MongoDB `fibo_v2`"
        )
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)


@contextmanager
def _tree_modules(tree: pathlib.Path) -> Iterator[dict[str, Any]]:
    """One example tree's modules, whatever ran before — evicted in and out."""
    saved = {n: sys.modules.pop(n, None) for n in COLLIDING}
    sys.path.insert(0, str(tree))
    try:
        import acquisition  # noqa: PLC0415
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415
        import projection  # noqa: PLC0415

        assert pathlib.Path(deployment.__file__).parent == tree, "the eviction did not hold"
        yield {"acquisition": acquisition, "deployment": deployment, "produce": produce, "projection": projection}
    finally:
        sys.path.remove(str(tree))
        for name in COLLIDING:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


@pytest.fixture(scope="module")
def modules() -> Iterator[dict[str, Any]]:
    with _tree_modules(EXAMPLE) as loaded:
        yield loaded


@pytest.fixture(scope="module")
def roles(estate: None, modules: dict[str, Any], tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    """`principal_id` → role, from the estate's own principal register."""
    deployment, acquisition = modules["deployment"], modules["acquisition"]
    with modules["produce"].product(tmp_path_factory.mktemp("roles")) as opened:
        mapped = dict(acquisition.principal_roles(relational_settings=opened.sources[deployment.SOURCE_RELATIONAL]))
    for principal_id in (*ENTITLED, KYC):
        assert principal_id in mapped, f"principal `{principal_id}` is not registered"
    return mapped


def _question(
    opened: OpenedProduct, deployment: Any, *, subject: str = SUBJECT, asked_at: datetime,
    known_as_of: datetime | None = None, debt_tolerance: str | None = None,
) -> ProductRequest:
    parameters: dict[str, Any] = {}
    if known_as_of is not None:
        parameters[deployment.KNOWN_AS_OF] = known_as_of.isoformat()
    if debt_tolerance is not None:
        parameters[deployment.DEBT_TOLERANCE] = debt_tolerance
    return opened.question(
        subject=subject, asked_at=asked_at, intent=QUESTION["question"]["intent"],
        freshness=QUESTION["question"]["freshness"], parameters=parameters,
    )


def _perspective(roles: dict[str, str], principal_id: str) -> Perspective:
    return Perspective(principal_id=principal_id, role=roles[principal_id])


@dataclass(frozen=True)
class _Served:
    """One served answer, still attached to the product it was asked of."""

    opened: OpenedProduct
    outcome: ServedProduct
    record: DecisionReplayRecord


def _serve(opened: OpenedProduct, modules: dict[str, Any], perspective: Perspective, **question: Any) -> _Served:
    outcome = opened.answer(_question(opened, modules["deployment"], **question), perspective=perspective)
    assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
    return _Served(opened=opened, outcome=outcome, record=opened.record_of(outcome))


@pytest.fixture(scope="module")
def wall(estate: None, modules: dict[str, Any], roles: dict[str, str], tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, _Served]]:
    """The demonstration question at `T1` under each entitled principal, each
    in its own opened product so each minted substrate is the one reopened."""
    opened_products: list[OpenedProduct] = []
    served: dict[str, _Served] = {}
    try:
        for principal_id in ENTITLED:
            opened = modules["produce"].product(tmp_path_factory.mktemp(principal_id.lower()))
            opened.__enter__()
            opened_products.append(opened)
            served[principal_id] = _serve(opened, modules, _perspective(roles, principal_id), asked_at=INSTANTS["T1"])
        yield served
    finally:
        for opened in reversed(opened_products):
            opened.__exit__(None, None, None)


class _FreshEnvironment:
    """A replay environment built from the RECORD and the deployment's own
    documents — no acquisition object, no live view from the serve."""

    def __init__(self, *, modules: dict[str, Any], opened: OpenedProduct, fabric: Any, record: DecisionReplayRecord) -> None:
        from ccf.deployment.operators import build_operator_registry  # noqa: PLC0415
        from ccf.products.provenance import EffectiveRequest  # noqa: PLC0415
        from ccf.products.resolver import build_governed_resolver  # noqa: PLC0415

        self._produce = modules["produce"]
        path = record.content_generation_path
        assert path.request is not None
        # Π is rebuilt from the EFFECTIVE request the record carries on
        # dimension 2 — the class defaults as they folded at decision time.
        resolution = record.policy_bindings.request_resolution
        effective = EffectiveRequest.model_validate_json(resolution) if isinstance(resolution, str) else resolution
        assert isinstance(effective, EffectiveRequest), resolution
        self._request = path.request.model_copy(update={"parameters": dict(effective.values())})
        self._required = tuple(path.operator_plan)
        arguments = opened.build_arguments(fabric)
        self._policy_key = arguments["policy_bundle_key"]
        self._ttl = int(CONFIG["ttl"]["product_ttl_seconds"])
        resolver = build_governed_resolver(**arguments)
        self._operators = build_operator_registry(
            parameters=resolver._operator_parameters(self._request),
            view=fabric.handle.reader.as_of(tenant_id=record.tenant_id, at=record.context_fabric_snapshot.temporal_boundary),
            pins=fabric.pins, policy_bundle_key=self._policy_key,
        )
        self.rehydrated = 0

    def resolve_plan(self, *, plan_id: str) -> Any:
        return self._produce.plan_factory(required=self._required, request=self._request)

    def resolve_operators(self, *, operator_keys: tuple[str, ...]) -> Any:
        return self._operators

    def rehydrate_product(self, *, record: DecisionReplayRecord, projection: Any) -> ContextProductContract:
        self.rehydrated += 1
        path, snapshot = record.content_generation_path, record.context_fabric_snapshot
        policy_versions = frozenset(b.version for b in record.policy_bindings.bindings if b.key == self._policy_key)
        # Every member the record carries is copied VERBATIM: the anchor
        # instant, the debt in force, the sources' recency, the obligation.
        return ContextProductContract(
            schema_name=CONFIG["product_class"]["schema_name"], schema_version=CONFIG["product_class"]["schema_version"],
            plan_id=projection.plan_id, tenant_id=record.tenant_id, temporal_boundary=snapshot.temporal_boundary,
            expires_at=(path.ttl_anchor_at or snapshot.temporal_boundary) + timedelta(seconds=self._ttl),
            ttl_anchor=CONFIG["product_class"]["ttl_anchor"], ttl_anchor_at=path.ttl_anchor_at,
            lineage=ProductLineage(operators_invoked=frozenset(path.operator_plan), policy_bundle_versions=policy_versions, graph_snapshot_at=snapshot.temporal_boundary),
            payload=projection.payload, debt=path.debt, debt_evidence=path.debt_evidence,
            source_refresh_recency=path.source_refresh_recency, obligation_in_force=path.obligation_in_force,
        )


@contextmanager
def _reopened_fabric(opened: OpenedProduct) -> Iterator[Any]:
    """The question's own minted substrate, reopened as the replay reader."""
    from ccf.deployment import load_config_and_boot  # noqa: PLC0415

    substrate = ENVIRONMENT["substrate"]
    minted = sorted(opened.scratch.glob(f"{substrate['prefix']}*{substrate['suffix']}"))[-1]
    fabric = load_config_and_boot(opened.config_path, registry=opened.control_plane, connection={"database_path": str(minted)})
    try:
        yield fabric
    finally:
        fabric.handle.close()


def _replay(modules: dict[str, Any], served: _Served) -> ReplayOutcome:
    """The served record, re-executed over its own reopened substrate."""
    with _reopened_fabric(served.opened) as fabric:
        environment = _FreshEnvironment(modules=modules, opened=served.opened, fabric=fabric, record=served.record)
        replayed = replay(
            record_address=served.outcome.replay_ref.content_address, store=served.opened.artifact_store,
            reader=fabric.handle.reader, control_plane=served.opened.control_plane, environment=environment,
        )
    assert environment.rehydrated == 1
    return replayed


def _issuer_uri(served: _Served, subject: str) -> str:
    """The issuer's L2-minted entity URI, read off the served record's own
    snapshot and confirmed against the reopened view — never a guessed hash."""
    with _reopened_fabric(served.opened) as fabric:
        view = fabric.handle.reader.as_of(tenant_id=served.record.tenant_id, at=served.record.context_fabric_snapshot.temporal_boundary)
        issuers = [record.claim for record in view.entities if record.claim.entity_class == "issuer"]
    assert len(issuers) == 1, f"the view holds {len(issuers)} issuer claims"
    assert issuers[0].attributes.get("lei") == subject
    assert issuers[0].entity_uri in served.record.context_fabric_snapshot.touched_entities
    return issuers[0].entity_uri


def _plan_id(served: _Served) -> str:
    return str(served.outcome.product.payload["plan"]["plan_id"])


def _refuse_kyc(opened: OpenedProduct, modules: dict[str, Any], roles: dict[str, str]) -> tuple[RefusalEnvelope, DecisionReplayRecord, str]:
    """The principal the estate holds no plan for, refused at the acquisition
    seam as data: the envelope, its record, and the record's address."""
    refused = opened.answer(_question(opened, modules["deployment"], asked_at=INSTANTS["T1"]), perspective=_perspective(roles, KYC))
    assert isinstance(refused, RefusalEnvelope), getattr(refused, "product", refused)
    # The shell discloses the minimum; the record retains the governed cause.
    assert refused.kind == "subject-unavailable" and refused.disclosure == "minimal"
    assert KYC not in refused.detail and "undisclosed" in refused.fields["cause"]
    return refused, opened.record_of(refused), opened.artifact_store.resolve_uri(uri=refused.replay_reference)


# --- G17: every record replays; the refused determination reconstructs -----------------


def test_each_principals_product_replays_and_the_ungranted_refusal_reconstructs(
    estate: None, modules: dict[str, Any], roles: dict[str, str], wall: dict[str, _Served], tmp_path: pathlib.Path
) -> None:
    """Replay rebuilds Π from the RECORDED request and re-executes over the
    recorded snapshot under the recorded principal — the banker's, the
    analyst's and the trader's products each hash to their served bytes; the
    three addresses differ, so three re-executions were held to three
    products. The principal the estate holds no plan for is refused at the
    acquisition seam as data; `replay_refusal` reconstructs that refusal with
    its cause and no product, and `replay()` refuses the same record by name
    (`D-IMPL-344`). The refusal is asked of a product that has already served
    a question, so the request-contract pin its record names is registered;
    asked first of a fresh product it is not (`CP17-F-09`, kept executable
    in the expected-failure test below).

    Declared product gate `MWE-G17` (`CP-SPEC-017` §G.1).
    """
    addresses: dict[str, str] = {}
    for principal_id, served in wall.items():
        replayed = _replay(modules, served)
        addresses[principal_id] = content_hash(served.outcome.product)
        assert replayed.product_content_address == addresses[principal_id]
        assert replayed.record_content_address == served.outcome.replay_ref.content_address
        assert replayed.product.payload["role"] == roles[principal_id] == served.record.perspective_conditioning.role
    assert len(set(addresses.values())) == len(ENTITLED), addresses

    with modules["produce"].product(tmp_path / "refused") as opened:
        _serve(opened, modules, _perspective(roles, BANKER), asked_at=INSTANTS["T1"])
        refused, record, address = _refuse_kyc(opened, modules, roles)
        with _reopened_fabric(opened) as fabric:
            environment = _FreshEnvironment(modules=modules, opened=opened, fabric=fabric, record=record)
            shared = {"record_address": address, "store": opened.artifact_store, "reader": fabric.handle.reader,
                      "control_plane": opened.control_plane, "environment": environment}
            reconstructed = replay_refusal(**shared)
            with pytest.raises(ReplayRecordKindMismatch):
                replay(**shared)
    assert isinstance(reconstructed, RefusalReplayOutcome)
    assert reconstructed.record_content_address == address and environment.rehydrated == 0
    assert reconstructed.assembly_refusal == record.content_generation_path.assembly_refusal
    for cause in (refused.kind, KYC, "unauthorized", "no-projection-plan"):
        assert cause in reconstructed.assembly_refusal, f"`{cause}` is not in the reconstructed block"
    assert reconstructed.record.perspective_conditioning.principal_id == KYC
    assert reconstructed.child_contract_addresses == ()
    assert "product" not in type(reconstructed).model_fields


# --- no gate: a first-question refusal pins a version nothing registered (CP17-F-09) ----


@pytest.mark.xfail(
    strict=True, raises=ReplayUnresolvable,
    reason="CP17-F-09: a refusal recorded at the acquisition seam pins the request-contract version that `_register` mints only on the served path, so the first question of a fresh Control Plane leaves a record replay cannot resolve",
)
def test_a_refusal_asked_first_of_a_fresh_product_reconstructs(
    estate: None, modules: dict[str, Any], roles: dict[str, str], tmp_path: pathlib.Path
) -> None:
    """The same refusal as the gate above, asked FIRST of a fresh product: the
    record pins `request_contract` at the content address the resolver would
    register, and nothing has registered it yet.
    """
    with modules["produce"].product(tmp_path / "fresh") as opened:
        _, record, address = _refuse_kyc(opened, modules, roles)
        with _reopened_fabric(opened) as fabric:
            environment = _FreshEnvironment(modules=modules, opened=opened, fabric=fabric, record=record)
            reconstructed = replay_refusal(
                record_address=address, store=opened.artifact_store, reader=fabric.handle.reader,
                control_plane=opened.control_plane, environment=environment,
            )
    assert reconstructed.assembly_refusal == record.content_generation_path.assembly_refusal


# --- no gate: the computed-empty serve cannot be rehydrated (CP17-F-08) ----------------


@pytest.mark.xfail(
    strict=True, raises=ReplayDivergence,
    reason="CP17-F-08: ContentGenerationPath carries no computed_empty, so a computed-empty serve cannot be rehydrated through the public replay seam",
)
def test_a_computed_empty_serve_replays_through_the_public_seam(
    estate: None, modules: dict[str, Any], roles: dict[str, str], tmp_path: pathlib.Path
) -> None:
    """A subject with no issuer row is SERVED computed-empty at the diagnostic
    tolerance; its record should replay to the served address like any other.
    It does not: the product hashes with its `computed_empty` finding and the
    record carries no member to rehydrate it from.
    """
    with modules["produce"].product(tmp_path / "empty") as opened:
        empty = _serve(
            opened, modules, _perspective(roles, BANKER), subject=NOBODY, asked_at=INSTANTS["T1"], debt_tolerance=DIAGNOSTIC_TOLERANCE,
        )
        assert empty.outcome.product.computed_empty is not None
        replayed = _replay(modules, empty)
    assert replayed.product_content_address == content_hash(empty.outcome.product)


# --- G11: the Reg FD boundary in the invalidation register --------------------------


def test_the_reg_fd_boundary_refuses_a_determination_that_touched_the_issuer_before_it(
    estate: None, modules: dict[str, Any], roles: dict[str, str], wall: dict[str, _Served], tmp_path: pathlib.Path
) -> None:
    """The Reg FD event is a boundary in the Control Plane's invalidation
    register, keyed on the issuer's L2 entity URI. Recorded AFTER the banker
    was served at `T0` and at `TW`, the same `T0` question is refused by the
    dependency-invalidation gate naming the issuer and the event; the question
    at `T1`, whose snapshot is at or after the boundary, still serves; and
    another issuer at `T0` still serves — the boundary is one entity's.

    Declared product gate `MWE-G11` (`CP-SPEC-017` §G.1).
    """
    banker = _perspective(roles, BANKER)
    disclosure = wall[BANKER].outcome.product.payload["issuer"]["reg_fd_disclosure"]
    assert disclosure is not None, "the issuer carries no Reg FD event at `T1`"
    boundary = datetime.combine(datetime.fromisoformat(disclosure["valid_from"]).date(), datetime.min.time(), tzinfo=UTC)
    assert INSTANTS["T0"] < boundary <= INSTANTS["T1"]

    with modules["produce"].product(tmp_path / "before") as opened:
        at_t0 = _serve(opened, modules, banker, asked_at=INSTANTS["T0"])
        issuer_uri = _issuer_uri(at_t0, SUBJECT)
    with modules["produce"].product(tmp_path / "wall") as opened:
        at_tw = _serve(opened, modules, banker, asked_at=INSTANTS["TW"])
        assert _issuer_uri(at_tw, SUBJECT) == issuer_uri

    with modules["produce"].product(tmp_path / "after") as opened:
        ControlPlaneInvalidationSink(registry=opened.control_plane).record(
            tenant_id=opened.tenant_id, entity_uri=issuer_uri, invalidated_from=boundary,
            reason=INVALIDATION_REASON, source=str(disclosure["event_id"]),
        )
        refused = opened.answer(_question(opened, modules["deployment"], asked_at=INSTANTS["T0"]), perspective=banker)
        assert isinstance(refused, RefusalEnvelope), getattr(refused, "product", refused)
        record = opened.record_of(refused)
        assert record.perspective_conditioning.principal_id == BANKER
        block = record.content_generation_path.assembly_refusal
        assert GATE_DEPENDENCY_INVALIDATION in block and issuer_uri in block
        assert str(disclosure["event_id"]) in block and boundary.isoformat() in block
        assert record.context_fabric_snapshot.temporal_boundary == INSTANTS["T0"]

        served_after = _serve(opened, modules, banker, asked_at=INSTANTS["T1"])
        assert content_hash(served_after.outcome.product) == content_hash(wall[BANKER].outcome.product)
        other = _serve(opened, modules, banker, subject=OTHER_ISSUER, asked_at=INSTANTS["T0"], debt_tolerance=DIAGNOSTIC_TOLERANCE)
        assert issuer_uri not in other.record.context_fabric_snapshot.touched_entities
        assert other.record.context_fabric_snapshot.temporal_boundary == INSTANTS["T0"]


# --- G19: no wall-decision input on the vessel or the record; the record replays ---------


def test_no_served_vessel_or_record_carries_a_wall_input_the_principal_is_not_entitled_to(
    estate: None, modules: dict[str, Any], wall: dict[str, _Served]
) -> None:
    """The crossing that keyed the wall, the restriction in force and every
    OTHER principal's plan are consumed at the acquisition seam and never
    written into a principal's fabric: no byte of any served vessel or of its
    replay record names them. The positive control is the principal's OWN
    plan, which both carry; and each record still replays to its served bytes.

    Declared product gate `MWE-G19` (`CP-SPEC-017` §G.1).
    """
    plans = {principal_id: _plan_id(served) for principal_id, served in wall.items()}
    assert len(set(plans.values())) == len(ENTITLED), plans
    for principal_id, served in wall.items():
        vessel = canonical_bytes(served.outcome.product).decode("utf-8")
        record = canonical_bytes(served.record).decode("utf-8")
        # The positive controls: the vessel carries the principal's OWN plan,
        # the record carries the principal's OWN identity and role.
        assert plans[principal_id] in vessel, f"`{principal_id}` does not carry its own plan"
        assert principal_id in record and served.record.perspective_conditioning.role in record
        foreign = [plans[other] for other in ENTITLED if other != principal_id]
        foreign += [other for other in ENTITLED if other != principal_id]
        for text in (vessel, record):
            for forbidden in (*WALL_INPUTS, *foreign):
                assert forbidden not in text, f"`{forbidden}` reached `{principal_id}`"
        assert _replay(modules, served).product_content_address == content_hash(served.outcome.product)
