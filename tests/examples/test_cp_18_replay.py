"""Replay of a ranking — `IBO-G06`, `IBO-G07`.

`examples/cp-18-ib-opportunity-synthesis` on the paved producer road
(`CP-SPEC-018`). The rung's sharpest obligation: **a weight change reorders
every list ever produced**, so a ranking is defensible only if the weights
that produced it are pinned. A ranking served under one weight version must
rebuild byte for byte from its own record after the Control Plane has moved
on — and the same record replayed against a DIFFERENT vector must diverge
rather than quietly agree.

Replay is rebuilt from the record alone: Pi comes from the recorded effective
request, the operators from the recorded plan, the snapshot from the recorded
temporal boundary. The weight vector is not resolved afresh; it is read out of
the recorded snapshot, which is the whole point of putting it there.

**Reads the estate, seeds nothing** (CLAUDE.md §9).
"""

from __future__ import annotations

import json
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
from ccf.projection.plan import Perspective
from ccf.replay.engine import ReplayDivergence, ReplayOutcome, replay
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-18-ib-opportunity-synthesis"

ESTATE_VARIABLES = (
    "CCF_CP_18_SQLITE_PATH", "CCF_CP_18_POSTGRES_DSN", "CCF_CP_18_POSTGRES_SCHEMA",
    "CCF_CP_18_FLUREE_URL", "CCF_CP_18_FLUREE_LEDGER", "CCF_CP_18_MONGO_URI",
    "CCF_CP_18_MONGO_DB",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")

CONFIG: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
ENVIRONMENT: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_environment.yaml").read_text(encoding="utf-8"))
QUESTION: dict[str, Any] = yaml.safe_load((EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
SUBJECT: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]
ASKED_AT = datetime.fromisoformat(QUESTION["question"]["asked_at"])
AS_OF: str = QUESTION["instants"]["ASKED_AT"]
SINCE: str = QUESTION["instants"]["SINCE"]
ROLE = "ma"


@pytest.fixture(scope="module")
def estate() -> None:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the cp-18 estate is not configured: {', '.join(missing)} unset"
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
    outcome: ServedProduct
    record: DecisionReplayRecord


@pytest.fixture(scope="module")
def ranking(estate: None, modules: dict[str, Any], tmp_path_factory: Any) -> Iterator[_Served]:
    """One ranking, served and held open so its own substrate can be reopened."""
    deployment = modules["deployment"]
    opened = modules["produce"].product(tmp_path_factory.mktemp("cp18-replay"))
    opened.__enter__()
    try:
        asked = opened.question(
            subject=SUBJECT, asked_at=ASKED_AT, intent=INTENT, freshness=FRESHNESS,
            parameters={deployment.AS_OF: AS_OF, deployment.SINCE: SINCE},
        )
        outcome = opened.answer(asked, perspective=Perspective(principal_id=SUBJECT, role=ROLE))
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        yield _Served(opened=opened, outcome=outcome, record=opened.record_of(outcome))
    finally:
        opened.__exit__(None, None, None)


class _FreshEnvironment:
    """A replay environment built from the RECORD and the deployment's own
    documents — no acquisition object and no live view from the serve.

    ``substitute_vector`` is the sabotage seam of `IBO-G07`: handed a
    different weight vector, the ranking is rebuilt against weights that did
    not govern and the replay must diverge.
    """

    def __init__(
        self, *, modules: dict[str, Any], opened: OpenedProduct, fabric: Any,
        record: DecisionReplayRecord, substitute_vector: dict[str, Any] | None = None,
    ) -> None:
        from ccf.deployment.operators import build_operator_registry  # noqa: PLC0415
        from ccf.products.provenance import EffectiveRequest  # noqa: PLC0415
        from ccf.products.resolver import build_governed_resolver  # noqa: PLC0415

        self._produce = modules["produce"]
        self._projection = modules["projection"]
        self._substitute = substitute_vector
        path = record.content_generation_path
        assert path.request is not None
        resolution = record.policy_bindings.request_resolution
        effective = EffectiveRequest.model_validate_json(resolution) if isinstance(resolution, str) else resolution
        self._request = path.request.model_copy(update={"parameters": dict(effective.values())})
        self._required = tuple(path.operator_plan)
        arguments = opened.build_arguments(fabric)
        self._policy_key = arguments["policy_bundle_key"]
        self._ttl = int(CONFIG["ttl"]["product_ttl_seconds"])
        resolver = build_governed_resolver(**arguments)
        self._operators = build_operator_registry(
            parameters=resolver._operator_parameters(self._request),
            view=fabric.handle.reader.as_of(
                tenant_id=record.tenant_id, at=record.context_fabric_snapshot.temporal_boundary
            ),
            pins=fabric.pins, policy_bundle_key=self._policy_key,
        )
        self.rehydrated = 0

    def resolve_plan(self, *, plan_id: str) -> Any:
        plan = self._produce.plan_factory(required=self._required, request=self._request)
        if self._substitute is None:
            return plan
        return _SubstitutedVector(plan, self._substitute)

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


class _SubstitutedVector:
    """A projection whose banker claim is re-read under a DIFFERENT vector.

    Structural, not a subclass: it exposes `plan_id`, `required_operators` and
    `invoke` and is therefore a projection by the SDK's own definition.
    """

    def __init__(self, inner: Any, vector: dict[str, Any]) -> None:
        self._inner, self._vector = inner, vector

    @property
    def plan_id(self) -> str:
        return self._inner.plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._inner.required_operators()

    def invoke(self, *, view: Any, **rest: Any) -> Any:
        swapped = _view_with_vector(view, self._vector)
        return self._inner.invoke(view=swapped, **rest)


def _view_with_vector(view: Any, vector: dict[str, Any]) -> Any:
    """The same view with the banker claim's weight vector replaced."""
    entities = []
    for record in view.entities:
        if record.claim.entity_class != "banker":
            entities.append(record)
            continue
        attributes = {**record.claim.attributes,
                      "weights_json": json.dumps(vector, sort_keys=True),
                      "weight_version": str(vector.get("weight_version", ""))}
        claim = record.claim.model_copy(update={"attributes": attributes})
        entities.append(record.model_copy(update={"claim": claim}))
    return view.model_copy(update={"entities": tuple(entities)})


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


def _replay(
    modules: dict[str, Any], served: _Served, *, substitute_vector: dict[str, Any] | None = None
) -> ReplayOutcome:
    with _reopened_fabric(served.opened) as fabric:
        environment = _FreshEnvironment(
            modules=modules, opened=served.opened, fabric=fabric, record=served.record,
            substitute_vector=substitute_vector,
        )
        replayed = replay(
            record_address=served.outcome.replay_ref.content_address, store=served.opened.artifact_store,
            reader=fabric.handle.reader, control_plane=served.opened.control_plane, environment=environment,
        )
    assert environment.rehydrated == 1
    return replayed


# =========================================================================
# IBO-G06 — the ranking replays under the version that served it
# =========================================================================


def test_a_ranking_replays_under_the_weight_version_that_served_it(
    estate: None, modules: dict[str, Any], ranking: _Served
) -> None:
    """The historical ranking rebuilds byte for byte from its own record.

    Declared product gate `IBO-G06` (`CP-SPEC-018` §G.1). The weight vector is
    read out of the RECORDED SNAPSHOT rather than resolved afresh, which is
    why moving the Control Plane to a later version cannot change what a past
    decision replays to. An examiner reviewing a ranking entered months ago
    evaluates it against the weights that were in force then.
    """
    replayed = _replay(modules, ranking)
    assert replayed.product_content_address == content_hash(ranking.outcome.product)
    assert replayed.record_content_address == ranking.outcome.replay_ref.content_address

    rebuilt, original = replayed.product.payload, ranking.outcome.product.payload
    assert rebuilt["weight_version"] == original["weight_version"]
    assert rebuilt["weight_version"], "the replayed ranking names no weight version"
    assert [row["lei"] for row in rebuilt["ranked_opportunities"]] == [
        row["lei"] for row in original["ranked_opportunities"]
    ], "the replayed ordering differs from the served one"
    assert rebuilt["optional_context"] == original["optional_context"]


# =========================================================================
# IBO-G07 — a different vector diverges rather than quietly agreeing
# =========================================================================


def test_a_replay_against_a_different_weight_vector_diverges(
    estate: None, modules: dict[str, Any], ranking: _Served
) -> None:
    """The sabotage of `IBO-G06`, executed rather than described.

    Declared product gate `IBO-G07` (`CP-SPEC-018` §G.1). The control IS the
    sabotage: the same record is replayed with the banker claim's weight
    vector replaced by one that inverts the two highest-spread signal types,
    and the engine refuses it as a divergence instead of returning an ordering
    that would read exactly like the original. The vector is the only thing
    that changed.
    """
    original = json.loads(_banker_attributes(ranking)["weights_json"])
    weights = dict(original["weights"])
    assert weights, "the served ranking carries no weight vector"
    # Invert the pricing: whatever was cheapest becomes dearest. A REAL
    # re-pricing, not a nonsense value, so the divergence is the ordering's.
    ordered = sorted(weights, key=lambda key: float(weights[key]))
    inverted = {key: weights[ordered[-1 - index]] for index, key in enumerate(ordered)}
    substitute = {**original, "weights": inverted, "weight_version": "sabotage-inverted"}

    with pytest.raises(ReplayDivergence):
        _replay(modules, ranking, substitute_vector=substitute)

    # And the un-sabotaged replay of the same record still agrees.
    assert _replay(modules, ranking).product_content_address == content_hash(ranking.outcome.product)


def _banker_attributes(served: _Served) -> dict[str, str]:
    """The banker claim as the recorded snapshot holds it."""
    with _reopened_fabric(served.opened) as fabric:
        view = fabric.handle.reader.as_of(
            tenant_id=served.record.tenant_id,
            at=served.record.context_fabric_snapshot.temporal_boundary,
        )
        bankers = [record.claim for record in view.entities if record.claim.entity_class == "banker"]
    assert len(bankers) == 1, f"the view holds {len(bankers)} banker claims"
    return dict(bankers[0].attributes)
