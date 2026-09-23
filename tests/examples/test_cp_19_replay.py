"""Replay of an AML adjudication — `ATM-G13`.

`examples/cp-19-aml-typology-match` on the paved producer road
(`CP-SPEC-019`). One property of what the tree RECORDS rather than of what it
serves: an adjudication rebuilds byte for byte from its own record, with the
posture that governed, the perspective's own plan and the advisory passages
the determination rested on — and the same replay, handed a DIFFERENT
posture instant, diverges rather than quietly agreeing.

Replay is rebuilt from the record alone: Π comes from the recorded effective
request, the operators from the recorded plan, the snapshot from the recorded
temporal boundary. No object survives from the serve.

**Reads the estate, seeds nothing** (CLAUDE.md §9). Nothing here pins an
estate count or a date; the instants come off `artifacts/question.yaml`.
"""

from __future__ import annotations

import os
import pathlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pytest
import yaml
from ccf.contracts.canonical import content_hash
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.products.product import OpenedProduct
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.engine import (
    ReplayDivergence,
    ReplayOutcome,
    ReplayUnresolvable,
    replay,
    replay_refusal,
)
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-19-aml-typology-match"

ESTATE_VARIABLES = (
    "CCF_CP_19_SQLITE_PATH", "CCF_CP_19_POSTGRES_DSN", "CCF_CP_19_POSTGRES_SCHEMA",
    "CCF_CP_19_FLUREE_URL", "CCF_CP_19_FLUREE_LEDGER", "CCF_CP_19_MONGO_URI",
    "CCF_CP_19_MONGO_DB",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")

CONFIG: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
ENVIRONMENT: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_environment.yaml").read_text(encoding="utf-8"))
QUESTION: dict[str, Any] = yaml.safe_load((EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
INSTANTS: dict[str, str] = QUESTION["instants"]
SUBJECT: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]
ASKED_AT = datetime.fromisoformat(QUESTION["question"]["asked_at"])

PERSPECTIVES = (
    Perspective(principal_id="PRIN-AML-L1", role="l1"),
    Perspective(principal_id="PRIN-AML-L2", role="l2"),
    Perspective(principal_id="PRIN-AML-EXAM", role="examiner"),
)


@pytest.fixture(scope="module")
def estate() -> None:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = (
            f"the cp-19 estate is not configured: {', '.join(missing)} unset."
            " Point them at the v2 namespaces — Fluree `fibo-v2`, PostgreSQL `ccf_v2`, MongoDB `fibo_v2`"
        )
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)


@contextmanager
def _tree_modules(tree: pathlib.Path) -> Iterator[dict[str, Any]]:
    saved = {name: sys.modules.pop(name, None) for name in COLLIDING}
    sys.path.insert(0, str(tree))
    try:
        import acquisition  # noqa: PLC0415
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415
        import projection  # noqa: PLC0415

        assert pathlib.Path(deployment.__file__).parent == tree, "the eviction did not hold"
        yield {"acquisition": acquisition, "deployment": deployment,
               "produce": produce, "projection": projection}
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


@dataclass(frozen=True)
class _Served:
    """One served answer, still attached to the product it was asked of."""

    opened: OpenedProduct
    perspective: Perspective
    outcome: ServedProduct
    record: DecisionReplayRecord


def _question(opened: OpenedProduct, modules: dict[str, Any], *, as_of: str) -> ProductRequest:
    return opened.question(
        subject=SUBJECT, asked_at=ASKED_AT, intent=INTENT, freshness=FRESHNESS,
        parameters={modules["deployment"].AS_OF: as_of, modules["deployment"].NETWORK_DEPTH: "2"},
    )


def _serve(opened: OpenedProduct, modules: dict[str, Any], perspective: Perspective, *, as_of: str) -> _Served:
    outcome = opened.answer(_question(opened, modules, as_of=as_of), perspective=perspective)
    assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
    return _Served(opened=opened, perspective=perspective, outcome=outcome, record=opened.record_of(outcome))


@pytest.fixture(scope="module")
def adjudications(
    estate: None, modules: dict[str, Any], tmp_path_factory: pytest.TempPathFactory
) -> Iterator[dict[str, _Served]]:
    """The demonstration alert under each perspective, each in its own opened
    product so the substrate reopened for replay is the one that question minted."""
    opened_products: list[OpenedProduct] = []
    served: dict[str, _Served] = {}
    try:
        for perspective in PERSPECTIVES:
            opened = modules["produce"].product(tmp_path_factory.mktemp(perspective.role))
            opened.__enter__()
            opened_products.append(opened)
            served[perspective.role] = _serve(
                opened, modules, perspective, as_of=INSTANTS["AS_OF_EARLY"]
            )
        yield served
    finally:
        for opened in reversed(opened_products):
            opened.__exit__(None, None, None)


class _FreshEnvironment:
    """A replay environment built from the RECORD and the deployment's own
    documents — no acquisition object and no live view from the serve.

    ``as_of_override`` is the sabotage seam: handed a different instant, Π is
    rebuilt against a posture that did not govern and the replay must diverge.
    """

    def __init__(
        self, *, modules: dict[str, Any], opened: OpenedProduct, fabric: Any,
        record: DecisionReplayRecord, as_of_override: str | None = None,
    ) -> None:
        from ccf.deployment.operators import build_operator_registry  # noqa: PLC0415
        from ccf.products.provenance import EffectiveRequest  # noqa: PLC0415
        from ccf.products.resolver import build_governed_resolver  # noqa: PLC0415

        self._produce = modules["produce"]
        path = record.content_generation_path
        assert path.request is not None
        # Π is rebuilt from the EFFECTIVE request on dimension 2 — the class
        # defaults exactly as they folded at decision time.
        resolution = record.policy_bindings.request_resolution
        effective = EffectiveRequest.model_validate_json(resolution) if isinstance(resolution, str) else resolution
        parameters = dict(effective.values())
        if as_of_override is not None:
            parameters[modules["deployment"].AS_OF] = as_of_override
        self._request = path.request.model_copy(update={"parameters": parameters})
        self._required = tuple(path.operator_plan)
        arguments = opened.build_arguments(fabric)
        self._policy_key = arguments["policy_bundle_key"]
        self._ttl = int(CONFIG["ttl"]["product_ttl_seconds"])
        resolver = build_governed_resolver(**arguments)
        self._operators = build_operator_registry(
            parameters=resolver.operator_parameters(self._request),
            view=fabric.handle.reader.as_of(
                tenant_id=record.tenant_id, at=record.context_fabric_snapshot.temporal_boundary
            ),
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
        policy_versions = frozenset(
            binding.version for binding in record.policy_bindings.bindings if binding.key == self._policy_key
        )
        return ContextProductContract(
            schema_name=CONFIG["product_class"]["schema_name"],
            schema_version=CONFIG["product_class"]["schema_version"],
            plan_id=projection.plan_id, tenant_id=record.tenant_id,
            temporal_boundary=snapshot.temporal_boundary,
            expires_at=(path.ttl_anchor_at or snapshot.temporal_boundary) + timedelta(seconds=self._ttl),
            ttl_anchor=CONFIG["product_class"]["ttl_anchor"], ttl_anchor_at=path.ttl_anchor_at,
            lineage=ProductLineage(
                operators_invoked=frozenset(path.operator_plan),
                policy_bundle_versions=policy_versions, graph_snapshot_at=snapshot.temporal_boundary,
            ),
            payload=projection.payload, debt=path.debt, debt_evidence=path.debt_evidence,
            source_refresh_recency=path.source_refresh_recency,
            obligation_in_force=path.obligation_in_force,
        )


@contextmanager
def _reopened_fabric(opened: OpenedProduct) -> Iterator[Any]:
    """The question's own minted substrate, reopened as the replay reader."""
    from ccf.deployment import load_config_and_boot  # noqa: PLC0415

    substrate = ENVIRONMENT["substrate"]
    minted = sorted(opened.scratch.glob(f"{substrate['prefix']}*{substrate['suffix']}"))[-1]
    fabric = load_config_and_boot(
        opened.config_path, registry=opened.control_plane, connection={"database_path": str(minted)}
    )
    try:
        yield fabric
    finally:
        fabric.handle.close()


def _replay(modules: dict[str, Any], served: _Served, *, as_of_override: str | None = None) -> ReplayOutcome:
    """The served record, re-executed over its own reopened substrate."""
    with _reopened_fabric(served.opened) as fabric:
        environment = _FreshEnvironment(
            modules=modules, opened=served.opened, fabric=fabric, record=served.record,
            as_of_override=as_of_override,
        )
        replayed = replay(
            record_address=served.outcome.replay_ref.content_address, store=served.opened.artifact_store,
            reader=fabric.handle.reader, control_plane=served.opened.control_plane, environment=environment,
        )
    assert environment.rehydrated == 1
    return replayed


# =========================================================================
# ATM-G13 — the determination replays with the posture, the plan and the passages
# =========================================================================


def test_a_served_adjudication_replays_from_its_own_record(
    estate: None, modules: dict[str, Any], adjudications: dict[str, _Served]
) -> None:
    """Each perspective's adjudication rebuilds byte for byte from its record,
    and what it rebuilds carries the three things an examiner has to see: the
    posture that governed, the perspective's own member shape, and the
    advisory passages the typology matches were anchored to.

    Declared product gate `ATM-G13` (`CP-SPEC-019` §G.1). The three addresses
    differ, so three re-executions were held to three distinct products rather
    than to one answer three times.
    """
    addresses: dict[str, str] = {}
    for role, served in adjudications.items():
        replayed = _replay(modules, served)
        addresses[role] = content_hash(served.outcome.product)
        assert replayed.product_content_address == addresses[role]
        assert replayed.record_content_address == served.outcome.replay_ref.content_address

        rebuilt, original = replayed.product.payload, served.outcome.product.payload
        assert rebuilt["perspective"] == role == served.record.perspective_conditioning.role
        assert rebuilt["posture"] == original["posture"], "the replayed posture is not the one that governed"
        assert rebuilt["posture"] is not None, "the adjudication rested on no posture at all"
        assert rebuilt["permitted_dispositions"] == original["permitted_dispositions"]
        assert set(rebuilt) == set(original), sorted(set(rebuilt) ^ set(original))
    assert len(set(addresses.values())) == len(PERSPECTIVES), addresses

    # The passages: carried by the examiner's shape, and rebuilt identically.
    examiner = adjudications["examiner"]
    trail = examiner.outcome.product.payload["reasoning_trail"]
    assert trail, "the examiner's adjudication rests on no advisory passage"
    assert _replay(modules, examiner).product.payload["reasoning_trail"] == trail


def test_a_replay_handed_a_different_posture_instant_diverges(
    estate: None, modules: dict[str, Any], adjudications: dict[str, _Served]
) -> None:
    """The sabotage of `ATM-G13`, executed rather than described.

    The same record, replayed with `as_of` moved across the posture boundary,
    rebuilds a determination against a posture that did not govern — and the
    engine refuses it as a divergence instead of returning an answer that
    would read exactly like the original. The instant is the only thing that
    changed.
    """
    served = adjudications["examiner"]
    assert served.outcome.product.payload["as_of"] == INSTANTS["AS_OF_EARLY"]
    with pytest.raises(ReplayDivergence):
        _replay(modules, served, as_of_override=INSTANTS["AS_OF_LATE"])
    # And the un-sabotaged replay of the same record still agrees.
    assert _replay(modules, served).product_content_address == content_hash(served.outcome.product)


# =========================================================================
# No gate: two recorded SDK gaps, measured a second time on this rung
# =========================================================================


@pytest.mark.xfail(
    strict=True, raises=ReplayDivergence,
    reason="CP17-F-08, second instance: ContentGenerationPath carries no computed_empty, so a computed-empty serve cannot be rehydrated through the public replay seam",
)
def test_a_computed_empty_serve_replays_through_the_public_seam(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """An alert id no estate row answers is SERVED computed-empty at the
    diagnostic tolerance; its record should replay to the served address like
    any other. It does not — the product hashes with its `computed_empty`
    finding and the record carries no member to rehydrate it from.

    Claims no gate. Kept executable so the gap is measured on every run of
    this rung rather than remembered from another one.
    """
    with modules["produce"].product(tmp_path / "empty") as opened:
        outcome = opened.answer(
            opened.question(
                subject="ALT-999999", asked_at=ASKED_AT, intent=INTENT, freshness=FRESHNESS,
                parameters={modules["deployment"].AS_OF: INSTANTS["AS_OF_EARLY"], "debt_tolerance": "1.0"},
            ),
            perspective=PERSPECTIVES[0],
        )
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        assert outcome.product.computed_empty is not None
        empty = _Served(opened=opened, perspective=PERSPECTIVES[0], outcome=outcome,
                        record=opened.record_of(outcome))
        replayed = _replay(modules, empty)
    assert replayed.product_content_address == content_hash(empty.outcome.product)


@pytest.mark.xfail(
    strict=True, raises=ReplayUnresolvable,
    reason="CP17-F-09, second instance: a refusal recorded at the acquisition seam pins the request-contract version the resolver registers only on the served path, so the first question of a fresh Control Plane leaves a record replay cannot resolve",
)
def test_a_seam_refusal_asked_first_of_a_fresh_product_reconstructs(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """The perspective this deployment maps no plan for is refused at the
    acquisition seam as data. Asked FIRST of a fresh product, the record it
    leaves pins a request-contract version nothing has registered yet.

    Claims no gate. The companion assertion — that the same refusal DOES
    reconstruct once the product has served a question — is what makes this a
    measurement of the ordering rather than of the refusal.
    """
    ungranted = Perspective(principal_id="PRIN-AML-XXX", role="unmapped")
    with modules["produce"].product(tmp_path / "fresh") as opened:
        refused = opened.answer(_question(opened, modules, as_of=INSTANTS["AS_OF_EARLY"]), perspective=ungranted)
        assert isinstance(refused, RefusalEnvelope), getattr(refused, "product", refused)
        record = opened.record_of(refused)
        address = opened.artifact_store.resolve_uri(uri=refused.replay_reference)
        with _reopened_fabric(opened) as fabric:
            environment = _FreshEnvironment(modules=modules, opened=opened, fabric=fabric, record=record)
            reconstructed = replay_refusal(
                record_address=address, store=opened.artifact_store, reader=fabric.handle.reader,
                control_plane=opened.control_plane, environment=environment,
            )
    assert reconstructed.assembly_refusal == record.content_generation_path.assembly_refusal
