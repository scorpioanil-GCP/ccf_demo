"""`D-IMPL-339` — acquire once, and expose the admitted child contracts to the parent.

**The requirement, restated so it cannot be narrowed.** A composite consumes
its children's **content and governing evidence**. Before this change the
parent's plan was built and executed before any child was dispatched, and the
`AdmittedChild` values were dropped the moment `compose_children` returned —
so the children governed the answer and could not fill it.

**The proofs the ruling requires**, each driven through the REAL composite
fixture — a real grant, a real dispatch through the child's own door, real
admission — and each phrased so that severing the mechanism it names turns it
red (see the sabotage record in the candidate's report):

| Proof | Test |
| --- | --- |
| Child-content dependence | `test_the_parent_payload_CHANGES_because_it_read_the_child` |
| Same acquisition | `test_the_child_is_acquired_ONCE_and_that_instance_serves_both_content_and_governance` |
| No source substitute | (the same test — the door is one-shot and the plan reads only the view) |
| Early failure | `test_a_known_blocking_outcome_prevents_child_dependent_projection` |
| Late refusal | `test_a_later_governing_failure_serves_nothing_and_keeps_the_acquired_evidence` |
| Compatibility | `test_a_legacy_factory_and_scorer_are_called_EXACTLY_as_before` |
| Child-aware C/S | `test_the_parents_own_child_dependent_C_reaches_its_assessment_per_request` |
| Replay | `test_a_fresh_environment_reconstructs_the_parent_with_providers_disabled` |
"""
from __future__ import annotations

import pathlib
from collections.abc import Iterator, Mapping
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import content_hash
from ccf.products.composition import compose_expiry, compose_lineage
from ccf.products.contract import MaxTTL, ProductLineage
from ccf.replay.engine import replay
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtAssessment, DebtFactors, DebtSignal, context_debt
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS, ChildContractView
from ccf.products.contract import ContextProductContract
from ccf.products.request import ProductRequest
from ccf.products.resolver import GovernedResolver
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from tests.products.composite_fixture import (
    CHILD_CLASS,
    _Booted,
    _child_door,
    ask_composite,
    boot_composite,
    build_composite,
)
from tests.products.test_resolver_seam import (
    POLICY_BUNDLE_KEY,
    PRODUCT_CLASS,
    PRODUCT_VERSION,
    THRESHOLD_PARAMETER,
    _ThresholdProjection,
    _arguments,
)

#: The key under which the parent's plan surfaces the CHILD's business value.
CHILD_VALUE_KEY = "child_threshold"

#: `DEBT_TOLERANCE_PARAMETER`, declared on the parent's request contract so a
#: class default is admissible (`D-IMPL-251` C1=A).
TOLERANCE_ARGUMENT = {
    "declaration": {
        "arguments": {
            "properties": {
                "debt_tolerance": {
                    "type": "number",
                    "description": "The caller's own D_c tolerance, if stated.",
                }
            }
        }
    }
}


# --- the deployment's side: a plan that READS its child, and a scorer that does --


class _ChildReadingPlan:
    """The parent's Π over its children's contracts — CP-14's shape in miniature.

    Reads the child's business value off the admitted CONTRACT it was handed
    and nothing else: no source, no door, no second acquisition.
    """

    def __init__(
        self,
        *,
        required: tuple[str, ...],
        request: ProductRequest,
        children: ChildContractView,
    ) -> None:
        self._required = required
        self._request = request
        self._children = children

    @property
    def plan_id(self) -> str:
        return PRODUCT_CLASS

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, Any],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        threshold = Decimal(str(self._request.parameters[THRESHOLD_PARAMETER]))
        child = self._children[CHILD_CLASS]
        return ProjectionOutput(
            plan_id=self.plan_id,
            payload={
                "role": perspective.role,
                "threshold": str(threshold),
                "assembled": len(list(view.entities)),
                CHILD_VALUE_KEY: child.payload["threshold"],
            },
        )


class _ChildReadingFactory:
    """A composite-capable factory: implements BOTH seams and records which ran."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, *, required: tuple[str, ...], request: ProductRequest) -> Any:
        self.calls.append("legacy")
        return _ThresholdProjection(required=required, request=request)

    def build_with_children(
        self,
        *,
        required: tuple[str, ...],
        request: ProductRequest,
        children: ChildContractView,
    ) -> Any:
        self.calls.append("children")
        return _ChildReadingPlan(required=required, request=request, children=children)


class _LegacyFactorySpy:
    """A factory implementing ONLY the original seam, recording exactly what it got."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kw: Any) -> Any:
        self.calls.append(dict(kw))
        return _ThresholdProjection(required=kw["required"], request=kw["request"])


def _assessment(freshness: Decimal, completeness: Decimal) -> DebtAssessment:
    factors = DebtFactors(
        freshness=freshness,
        completeness=completeness,
        semantic_consistency=Decimal("1"),
    )
    return DebtAssessment(
        debt=context_debt(factors), signal=DebtSignal.OK, factors=factors, scorers=()
    )


class _LegacyScorerSpy:
    """A scorer implementing ONLY the original seam."""

    def __init__(self, *, freshness: Decimal = Decimal("1")) -> None:
        self.calls: list[set[str]] = []
        self._freshness = freshness

    def __call__(self, **kw: Any) -> DebtAssessment:
        self.calls.append(set(kw))
        return _assessment(self._freshness, Decimal("1"))


class _LegsScorer:
    """A child-aware scorer: the parent's own `C` reads what its child reported.

    `C = 1` when the child reported a threshold at or above 1500, `0.5`
    otherwise — a stand-in for CP-14's `legs_present`, read off the admitted
    contract per request and never re-derived from the estate.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, *, view: GraphView, evidence: Any = None) -> DebtAssessment:
        self.calls.append("legacy")
        return _assessment(Decimal("1"), Decimal("1"))

    def score_with_children(
        self, *, view: GraphView, evidence: Any, children: ChildContractView
    ) -> DebtAssessment:
        self.calls.append("children")
        reported = Decimal(children[CHILD_CLASS].payload["threshold"])
        return _assessment(Decimal("1"), Decimal("1") if reported >= 1500 else Decimal("0.5"))


def _one_shot(inner: Any) -> Any:
    """A door that answers ONCE and raises on any second acquisition."""
    calls: list[Mapping[str, str]] = []

    def door(arguments: Mapping[str, str]) -> Mapping[str, str]:
        calls.append(dict(arguments))
        if len(calls) > 1:
            raise RuntimeError(
                "the child was acquired a SECOND time; D-IMPL-339 acquires once"
            )
        return inner(arguments)

    door.calls = calls  # type: ignore[attr-defined]
    return door


class _Asking:
    """What the child is asked — the ONE input a test varies between two serves.

    A grant artifact is single-use, so a second `build_composite` on one
    fabric is refused; and the proof wants every other parent input fixed
    anyway. One resolver, one grant, one child resolver — and the threshold
    the child is asked for is the only thing that moves.
    """

    def __init__(self, threshold: str = "1000") -> None:
        self.threshold = threshold

    def __call__(self, requirement: Any, asked_at: datetime) -> dict[str, str]:
        return {"subject": "acct-1", "asked_at": asked_at.isoformat(), "threshold": self.threshold}


# --- fixtures and helpers -----------------------------------------------------


@pytest.fixture
def booted(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    yield from boot_composite(tmp_path)


@pytest.fixture
def booted_with_a_tight_tolerance(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    yield from boot_composite(
        tmp_path,
        product_class_overrides={"serve_obligations": {"default_debt_tolerance": "0.10"}},
        request_contract_overrides=TOLERANCE_ARGUMENT,
    )


def _wired(
    booted: _Booted,
    *,
    asking: _Asking | None = None,
    grant: bool = True,
    door: Any = None,
    **overrides: Any,
) -> GovernedResolver:
    """`build_composite`'s wiring — built ONCE per fabric — with overrides."""
    _resolver, children = build_composite(
        booted,
        grant=grant,
        child_arguments=asking or _Asking(),
        child_door=door or _child_door(booted),
    )
    arguments = _arguments(booted)
    arguments.update(composite_children=children, **overrides)
    return GovernedResolver(**arguments)


def _record(booted: _Booted, address: str) -> DecisionReplayRecord:
    """Off a FRESH store instance — nothing the serving path held in memory."""
    fresh = FileArtifactStore(root=booted.store.root)
    return DecisionReplayRecord.model_validate_json(fresh.get(content_address=address))


def _served(booted: _Booted, outcome: Any) -> tuple[ContextProductContract, DecisionReplayRecord]:
    assert isinstance(outcome, ServedProduct), outcome
    return outcome.product, _record(booted, outcome.replay_ref.content_address)


def _refused(booted: _Booted, outcome: Any, kind: str) -> DecisionReplayRecord:
    assert not isinstance(outcome, ServedProduct), outcome
    assert outcome.kind == kind, outcome.kind
    fresh = FileArtifactStore(root=booted.store.root)
    return DecisionReplayRecord.model_validate_json(
        fresh.get(content_address=fresh.resolve_uri(uri=outcome.replay_reference))
    )


# --- child-content dependence, same acquisition, no source substitute -----------


def test_the_parent_payload_CHANGES_because_it_read_the_child(booted: _Booted) -> None:
    """Two valid children differing in a business value; every other parent
    input fixed; the child's governance factors equivalent. The parent's
    corresponding payload value changes — and ONLY that value.

    Governance equivalence is asserted, not assumed, so a debt or expiry
    change cannot masquerade as evidence that the parent read its content.
    """
    factory, asking = _ChildReadingFactory(), _Asking("1000")
    resolver = _wired(booted, asking=asking, plan_factory=factory)
    first, first_record = _served(booted, ask_composite(resolver))
    asking.threshold = "2000"
    second, second_record = _served(booted, ask_composite(resolver))

    # The child's business value reached the parent's payload, from the view.
    assert first.payload[CHILD_VALUE_KEY] == "1000"
    assert second.payload[CHILD_VALUE_KEY] == "2000"
    assert factory.calls == ["children", "children"], factory.calls

    # Everything else about the two parents is identical: same request, same
    # own assessment, same expiry floor, same lineage union.
    assert first.debt == second.debt
    assert first.expires_at == second.expires_at
    assert first.lineage == second.lineage
    differing = {k for k in first.payload if first.payload[k] != second.payload.get(k)}
    assert differing == {CHILD_VALUE_KEY}, differing

    # And the CHILD's governance was equivalent across the two: same factors,
    # same expiry, same schema — only its content differed.
    (row_a,), (row_b,) = (
        first_record.content_generation_path.child_resolutions,
        second_record.content_generation_path.child_resolutions,
    )
    assert row_a.outcome_status == row_b.outcome_status == "admitted"
    assert row_a.child_debt_factors == row_b.child_debt_factors
    assert row_a.child_expires_at == row_b.child_expires_at
    assert row_a.child_content_address != row_b.child_content_address


def test_the_child_is_acquired_ONCE_and_that_instance_serves_both_content_and_governance(
    booted: _Booted,
) -> None:
    """The door answers once. The payload value and the recorded row both
    describe THAT answer — the same admitted product, not a second
    acquisition, a fresh lookup, or a separately reconstructed contract. The
    door raises on any second call, so a source substitute during projection
    would surface here as an error rather than as a quietly equal payload.
    """
    door = _one_shot(_child_door(booted))
    product, record = _served(
        booted, ask_composite(_wired(booted, door=door, plan_factory=_ChildReadingFactory()))
    )
    assert len(door.calls) == 1, door.calls
    (row,) = record.content_generation_path.child_resolutions
    assert row.outcome_status == "admitted"
    # The retained contract the parent read IS the admitted product on the row.
    fresh = FileArtifactStore(root=booted.store.root)
    assert row.child_content_address is not None
    retained = ContextProductContract.model_validate_json(
        fresh.get(content_address=row.child_content_address)
    )
    assert retained.payload["threshold"] == product.payload[CHILD_VALUE_KEY] == "1000"
    assert retained.schema_name == CHILD_CLASS


# --- early failure ---------------------------------------------------------------


def test_a_known_blocking_outcome_prevents_child_dependent_projection(booted: _Booted) -> None:
    """A required child absent (no in-force grant): the parent's plan is never
    built, the refusal is recorded like a pre-assembly refusal — nothing
    read — and every child row the walk produced is on it.
    """
    factory = _ChildReadingFactory()
    record = _refused(
        booted, ask_composite(_wired(booted, grant=False, plan_factory=factory)), "composite-child-refusal"
    )
    assert factory.calls == [], factory.calls
    assert record.content_generation_path.steps == ()
    (row,) = record.content_generation_path.child_resolutions
    assert row.outcome_status == "no-producing-skill"
    assert row.required is True


def test_an_invoked_child_that_refuses_admission_ALSO_blocks_projection(booted: _Booted) -> None:
    """The other blocking case: the child was dispatched and served, then
    refused at admission (answered at a different instant). Still no plan.
    """
    factory = _ChildReadingFactory()

    def a_day_late(requirement: Any, asked_at: datetime) -> dict[str, str]:
        return {"subject": "acct-1", "asked_at": (asked_at + timedelta(days=1)).isoformat(), "threshold": "1000"}

    _resolver, children = build_composite(booted, child_arguments=a_day_late)
    arguments = _arguments(booted)
    arguments.update(composite_children=children, plan_factory=factory)
    record = _refused(booted, ask_composite(GovernedResolver(**arguments)), "composite-child-refusal")
    assert factory.calls == [], factory.calls
    (row,) = record.content_generation_path.child_resolutions
    assert row.refusal_ref == "as-of-mismatch"
    assert row.child_reported_address


# --- late refusal ------------------------------------------------------------------


def test_a_later_governing_failure_serves_nothing_and_keeps_the_acquired_evidence(
    booted_with_a_tight_tolerance: _Booted,
) -> None:
    """The plan ran over the child (the payload WAS computed), then the
    tolerance comparison refused. The computed payload is provisional and is
    not served; the acquisition happened exactly once; and the acquired child
    evidence is retained on the record.
    """
    booted = booted_with_a_tight_tolerance
    factory = _ChildReadingFactory()
    door = _one_shot(_child_door(booted))
    outcome = ask_composite(
        _wired(booted, door=door, plan_factory=factory, debt_scorer=_LegacyScorerSpy(freshness=Decimal("0.8")))
    )
    record = _refused(booted, outcome, "tolerance-exceeded")
    assert factory.calls == ["children"], factory.calls  # computed, provisional
    assert len(door.calls) == 1
    rows = record.content_generation_path.child_resolutions
    assert rows and rows[0].outcome_status == "admitted", rows  # `D-IMPL-338`


# --- compatibility ------------------------------------------------------------------


def test_a_legacy_factory_and_scorer_are_called_EXACTLY_as_before(booted: _Booted) -> None:
    """A composite whose factory and scorer implement only the original seams
    is served exactly as it was: `plan_factory(required=, request=)` and
    `debt_scorer(view=, evidence=)`, no extra keyword, no probing.
    """
    factory, scorer = _LegacyFactorySpy(), _LegacyScorerSpy()
    product, record = _served(booted, ask_composite(_wired(booted, plan_factory=factory, debt_scorer=scorer)))
    assert [set(c) for c in factory.calls] == [{"required", "request"}], factory.calls
    assert scorer.calls == [{"view", "evidence"}], scorer.calls
    assert CHILD_VALUE_KEY not in product.payload
    (row,) = record.content_generation_path.child_resolutions
    assert row.outcome_status == "admitted"  # governance still composed


# --- child-aware C/S ---------------------------------------------------------------


def test_the_parents_own_child_dependent_C_reaches_its_assessment_per_request(
    booted: _Booted,
) -> None:
    """The parent's `C` is read off the admitted child's contract, per
    request, through the same view the plan received. Two children, two
    different `C`, two different `D_c` — from the SAME kind of scorer call.
    """
    scorer, asking = _LegsScorer(), _Asking("1000")
    resolver = _wired(booted, asking=asking, plan_factory=_ChildReadingFactory(), debt_scorer=scorer)
    low, _ = _served(booted, ask_composite(resolver))
    asking.threshold = "2000"
    high, _ = _served(booted, ask_composite(resolver))
    assert scorer.calls == ["children", "children"], scorer.calls
    assert low.debt is not None and high.debt is not None
    assert low.debt.factors.completeness == Decimal("0.5")
    assert high.debt.factors.completeness == Decimal("1")
    assert low.debt.debt > high.debt.debt


# --- replay --------------------------------------------------------------------------


class _FreshEnvironment:
    """A replay environment built from the RECORD and deployment configuration.

    Holds no resolver, no ledger, no door, no live object from the serving
    run — the plan is rebuilt from the recorded request and the children
    :func:`~ccf.replay.engine.replay` reconstructed from the retained
    contracts; the product envelope is rebuilt from dimension 5 and the child
    rows, exactly as `R5` proved it can be.
    """

    def __init__(
        self, *, request: ProductRequest, required: tuple[str, ...], operators: Any, ttl_seconds: int
    ) -> None:
        self._request = request
        self._required = required
        self._operators = operators
        self._ttl = ttl_seconds

    def resolve_plan(self, *, plan_id: str) -> Any:
        raise LookupError(f"{plan_id!r} is a composite plan and needs its children")

    def resolve_composite_plan(self, *, plan_id: str, children: ChildContractView) -> Any:
        if plan_id != PRODUCT_CLASS:
            raise LookupError(plan_id)
        return _ChildReadingPlan(
            required=tuple(self._required), request=self._request, children=children
        )

    def resolve_operators(self, *, operator_keys: tuple[str, ...]) -> Any:
        return self._operators

    def rehydrate_product(self, *, record: DecisionReplayRecord, projection: Any) -> ContextProductContract:
        path, snapshot = record.content_generation_path, record.context_fabric_snapshot
        rows = tuple(r for r in path.child_resolutions if r.outcome_status == "admitted")
        own = ProductLineage(
            operators_invoked=frozenset(path.operator_plan),
            policy_bundle_versions=frozenset(
                b.version for b in record.policy_bindings.bindings if b.key == POLICY_BUNDLE_KEY
            ),
            graph_snapshot_at=snapshot.temporal_boundary,
        )
        lineage = compose_lineage(
            [
                own,
                *(
                    ProductLineage(
                        operators_invoked=r.child_operators_invoked or frozenset(),
                        policy_bundle_versions=r.child_policy_bundle_versions or frozenset(),
                        graph_snapshot_at=r.child_graph_snapshot_at or snapshot.temporal_boundary,
                    )
                    for r in rows
                ),
            ]
        )
        return ContextProductContract(
            schema_name=PRODUCT_CLASS,
            schema_version=PRODUCT_VERSION,
            plan_id=projection.plan_id,
            tenant_id=record.tenant_id,
            temporal_boundary=snapshot.temporal_boundary,
            expires_at=compose_expiry(
                constituent_validities=[r.child_expires_at for r in rows if r.child_expires_at],
                max_ttl=MaxTTL(seconds=self._ttl),
                ttl_anchor_at=record.recorded_at,
            ),
            ttl_anchor="from_decision",
            # `D-IMPL-341`: the anchor instant comes off the record, never recomputed.
            ttl_anchor_at=path.ttl_anchor_at,
            lineage=lineage,
            payload=projection.payload,
            debt=path.debt,
            debt_evidence=path.debt_evidence,
            source_refresh_recency=path.source_refresh_recency,
            obligation_in_force=path.obligation_in_force,
        )


def test_a_fresh_environment_reconstructs_the_parent_with_providers_disabled(
    booted: _Booted,
) -> None:
    """Replay rebuilds the child-contract view from the RETAINED contracts —
    resolved by content address off a fresh store instance — hands it to the
    child-dependent plan BEFORE re-execution, and reproduces the parent's
    bytes exactly. The child's door is one-shot, so any provider call during
    replay raises; the environment holds no live object from the serve.
    """
    door = _one_shot(_child_door(booted))
    served = ask_composite(_wired(booted, door=door, plan_factory=_ChildReadingFactory()))
    product, record = _served(booted, served)
    assert product.payload[CHILD_VALUE_KEY] == "1000"

    fresh_store = FileArtifactStore(root=booted.store.root)
    path = record.content_generation_path
    # Operators come from the deployment's registry builder, as every replay
    # environment supplies them — from the RECORDED request and the recorded
    # temporal boundary, not from the serving run.
    from ccf.deployment.operators import build_operator_registry

    configuration = GovernedResolver(**{**_arguments(booted), "composite_children": None})
    environment = _FreshEnvironment(
        request=path.request,
        required=tuple(path.operator_plan),
        operators=build_operator_registry(
            parameters=configuration._operator_parameters(path.request),
            view=booted.fabric.handle.reader.as_of(
                tenant_id=record.tenant_id,
                at=record.context_fabric_snapshot.temporal_boundary,
            ),
            pins=booted.fabric.pins,
            policy_bundle_key=POLICY_BUNDLE_KEY,
        ),
        ttl_seconds=_arguments(booted)["product_ttl_seconds"],
    )

    outcome = replay(
        record_address=served.replay_ref.content_address,
        store=fresh_store,
        reader=booted.fabric.handle.reader,
        control_plane=booted.control_plane,
        environment=environment,
    )
    assert outcome.product_content_address == content_hash(product)
    assert outcome.product.payload[CHILD_VALUE_KEY] == "1000"
    assert len(door.calls) == 1, "replay reached the provider"
    # The contract replay rebuilt the view from is the one the row names.
    (row,) = record.content_generation_path.child_resolutions
    assert row.child_content_address is not None
    assert fresh_store.exists(content_address=row.child_content_address)
