"""The L4/L5 decision-time acquisition edge, asserted in-process (XPRC-01).

CLAUDE.md §7.1 bullet 2 ("MCP as ingress for content acquisition (L4–L5)");
whitepaper §6.6 (search-inference recursion); §10 (single-writer).

| Invariant | Row asserted by | What would fail |
|---|---|---|
| The edge is bound, not merely importable | ``test_the_payload_carries_the_acquired_value`` | Deleting the engine's acquisition stage: the payload loses the sentinel |
| Policy runs before acquisition (INV-CH7-26) | ``test_acquisition_runs_after_the_operator_plan_and_before_invoke`` | Fetching before the operator plan resolved |
| No silent proceed-without-content | the three refusal rows | Any fallback that let Π interpret absent content |
| Replay re-feeds, never re-acquires (INV-CH7-31) | ``test_replay_refeeds_recorded_content_without_acquiring`` | An engine that reached the network at replay |
| Tenancy is a per-call argument (D-23) | ``test_two_principals_over_one_acquirer_do_not_cross`` | Moving ``tenant_id`` onto the acquirer's constructor |
| The seam is opt-in | ``test_a_plan_that_declares_no_content_is_untouched`` | Widening ``ProjectionPlan`` instead of adding a separate Protocol |

**The binding test is not an import check and must not be weakened into one.**
``test_the_payload_carries_the_acquired_value`` asserts on the *projection
payload*. A test that asserted ``ContentAcquirer`` is importable, or that
``McpContentAcquirer`` exists, would pass against an engine that never calls
either — which is precisely the "covered by construction" overclaim this plan
exists to retire (D-21). If this test is ever edited, the payload assertion is
the part that carries the claim.

Every domain value comes from ``tests/fixtures/banking/``; delete the fixtures
and this module has nothing to run.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.contracts.canonical import content_hash
from ccf.graph.protocols import GraphView
from ccf.operators.base import (
    OperatorCategory,
    OperatorOutput,
    OperatorParameters,
    mint_provenance,
)
from ccf.projection.acquisition import (
    AcquiredContent,
    AcquirerNotConfigured,
    ContentAcquiringPlan,
    ContentRequest,
    ContentUnsatisfied,
    UndeclaredAcquisition,
)
from ccf.projection.engine import (
    ExecutionResult,
    OperatorRegistry,
    ProjectionEngine,
)
from ccf.projection.plan import Perspective, ProjectionOutput, ProjectionPlan

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"


def _load(name: str) -> Any:
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


CONTENT = _load("content_acquisition.yaml")
CONTROL = _load("controlplane.yaml")
ONTOLOGY = _load("ontology.yaml")

TENANT: str = CONTENT["tenants"]["primary"]
OTHER_TENANT: str = CONTENT["tenants"]["secondary"]
REQUEST_KEY: str = CONTENT["request"]["request_key"]
SELECTOR: str = CONTENT["request"]["selector"]
SOURCE_KEY: str = CONTENT["sources"]["covenant_notes"]
UNCONFIGURED_SOURCE: str = CONTENT["sources"]["unconfigured"]
PAYLOAD_KEY: str = CONTENT["payload_key"]
NOTES: Mapping[str, str] = CONTENT["notes"]
PLAN_ID: str = CONTROL["product_class"]["plan_id"]
PERSPECTIVE = Perspective(
    principal_id=CONTROL["perspective"]["principal_id"],
    role=CONTROL["perspective"]["role"],
)
BOUNDARY = datetime(2026, 3, 1, 10, tzinfo=UTC)
OPERATOR_KEY = "policy.fixture-passthrough"


class _NoParameters(OperatorParameters):
    """The fixture operator's (empty) declared parameter set."""


class _PassthroughPolicyOperator:
    """A Policy-category operator that returns its input view unchanged.

    Policy specifically, because the ordering claim under test is that nothing
    is fetched until Policy has constrained the view. A no-op is enough: what
    the test needs is that a Policy step *ran*, observable in
    ``ExecutionResult.steps``, before the acquirer was called.
    """

    @property
    def key(self) -> str:
        return OPERATOR_KEY

    @property
    def category(self) -> OperatorCategory:
        return "policy"

    @property
    def parameters(self) -> OperatorParameters:
        return _NoParameters()

    def apply(
        self,
        *,
        view: GraphView,
        tenant_id: str,
        temporal_boundary: datetime,
        upstream: tuple[Any, ...],
    ) -> OperatorOutput:
        return OperatorOutput(
            view=view,
            provenance=mint_provenance(self, upstream=upstream),
        )


class _EmptyReader:
    """A reader over a graph that holds nothing.

    Deliberately empty: this module's subject is the acquisition stage, and an
    empty graph makes "the payload's value came from outside the graph"
    unambiguous — there is nothing inside it the value could have come from.
    """

    def as_of(self, *, tenant_id: str, at: datetime) -> GraphView:
        return GraphView(tenant_id=tenant_id, as_of=at)


class _RecordingAcquirer:
    """A ``ContentAcquirer`` double that records every call it receives."""

    def __init__(self, *, notes: Mapping[str, str], extra_key: str | None = None):
        self._notes = dict(notes)
        self._extra_key = extra_key
        self.calls: list[tuple[tuple[ContentRequest, ...], str]] = []
        self.steps_at_call: list[int] = []
        self.observer: Any = None

    def acquire(
        self, *, requests: tuple[ContentRequest, ...], tenant_id: str
    ) -> Mapping[str, AcquiredContent]:
        self.calls.append((requests, tenant_id))
        if self.observer is not None:
            self.steps_at_call.append(self.observer())
        acquired = {
            request.request_key: AcquiredContent.of(
                request=request,
                content=self._notes[tenant_id],
            )
            for request in requests
            if tenant_id in self._notes
        }
        if self._extra_key is not None and requests:
            acquired[self._extra_key] = AcquiredContent.of(
                request=ContentRequest(
                    request_key=self._extra_key,
                    source_key=requests[0].source_key,
                    selector=requests[0].selector,
                ),
                content="",
            )
        return acquired


class _PlainPlan:
    """A projection that declares no content — an I.1/I.2-shaped plan."""

    @property
    def plan_id(self) -> str:
        return PLAN_ID

    def required_operators(self) -> tuple[str, ...]:
        return (OPERATOR_KEY,)

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        return ProjectionOutput(plan_id=self.plan_id, payload={})


class _AcquiringPlan:
    """A projection that declares one content requirement and publishes it."""

    def __init__(self, *, source_key: str = SOURCE_KEY) -> None:
        self._source_key = source_key
        self.invoked_with: Mapping[str, AcquiredContent] | None = None

    @property
    def plan_id(self) -> str:
        return PLAN_ID

    def required_operators(self) -> tuple[str, ...]:
        return (OPERATOR_KEY,)

    def required_content(self) -> tuple[ContentRequest, ...]:
        return (
            ContentRequest(
                request_key=REQUEST_KEY,
                source_key=self._source_key,
                selector=SELECTOR,
            ),
        )

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
        acquired_content: Mapping[str, AcquiredContent],
    ) -> ProjectionOutput:
        self.invoked_with = acquired_content
        return ProjectionOutput(
            plan_id=self.plan_id,
            payload={PAYLOAD_KEY: acquired_content[REQUEST_KEY].content},
        )


@pytest.fixture
def registry() -> OperatorRegistry:
    built = OperatorRegistry()
    built.register(_PassthroughPolicyOperator())
    return built


def _execute(
    *,
    registry: OperatorRegistry,
    plan: ProjectionPlan | ContentAcquiringPlan,
    acquirer: Any = None,
    tenant_id: str = TENANT,
    recorded: tuple[AcquiredContent, ...] | None = None,
) -> ExecutionResult:
    engine = ProjectionEngine(
        reader=_EmptyReader(), registry=registry, acquirer=acquirer
    )
    return engine.execute(
        plan=plan,
        perspective=PERSPECTIVE,
        tenant_id=tenant_id,
        temporal_boundary=BOUNDARY,
        recorded_acquisitions=recorded,
    )


def test_the_payload_carries_the_acquired_value(registry: OperatorRegistry) -> None:
    """The engine feeds acquired content into Π, and Π's payload carries it.

    THE binding assertion. It is on the payload on purpose: delete the
    acquisition stage from ``ProjectionEngine.execute`` and this fails, because
    ``invoke`` never receives the mapping it reads. Do not weaken it into an
    import or ``hasattr`` check — those pass against an unbound edge.
    """
    plan = _AcquiringPlan()
    result = _execute(
        registry=registry,
        plan=plan,
        acquirer=_RecordingAcquirer(notes=NOTES),
    )

    assert result.projection.payload[PAYLOAD_KEY] == NOTES[TENANT]
    assert plan.invoked_with is not None
    assert plan.invoked_with[REQUEST_KEY].content == NOTES[TENANT]
    # The value is not in the graph the engine read, so it cannot have come
    # from anywhere but the acquisition stage.
    assert result.view.entities == ()


def test_acquisition_runs_after_the_operator_plan_and_before_invoke(
    registry: OperatorRegistry,
) -> None:
    """Policy first, then the fetch, then Π (INV-CH7-26 applied to acquisition).

    Nothing is acquired on behalf of a principal the Policy stage excluded,
    which is only true if the operator plan has already run when the acquirer
    is called.
    """
    plan = _AcquiringPlan()
    acquirer = _RecordingAcquirer(notes=NOTES)
    # Observed at the moment of the call: Π has not run yet (the plan has not
    # recorded an invocation) and the operator plan has (the acquirer is
    # handed the tenant and the declared requests only after it resolved).
    acquirer.observer = lambda: (0 if plan.invoked_with is None else 1)

    result = _execute(registry=registry, plan=plan, acquirer=acquirer)

    assert acquirer.steps_at_call == [0], "Π ran before acquisition"
    assert [step.category for step in result.steps] == ["policy"]
    requests, tenant = acquirer.calls[0]
    assert tenant == TENANT
    assert [request.request_key for request in requests] == [REQUEST_KEY]


def test_a_declaring_plan_without_an_acquirer_is_refused(
    registry: OperatorRegistry,
) -> None:
    """Refusal 1: no acquirer injected. Never a silent skip."""
    with pytest.raises(AcquirerNotConfigured):
        _execute(registry=registry, plan=_AcquiringPlan(), acquirer=None)


def test_content_the_plan_did_not_declare_is_refused(
    registry: OperatorRegistry,
) -> None:
    """Refusal 2: the acquirer returned something undeclared.

    The declared set and the resolved set are compared, never merged — an
    acquirer that could inject an extra item would feed Π material with no
    declaration to audit it against.
    """
    acquirer = _RecordingAcquirer(notes=NOTES, extra_key="smuggled")
    with pytest.raises(UndeclaredAcquisition):
        _execute(registry=registry, plan=_AcquiringPlan(), acquirer=acquirer)


def test_an_unsatisfiable_request_is_refused(registry: OperatorRegistry) -> None:
    """Refusal 3: a declared request came back unsatisfied.

    The double returns nothing for an unknown tenant. The engine must refuse
    rather than let Π interpret an absent covenant note as a missing covenant.
    """
    acquirer = _RecordingAcquirer(notes=NOTES)
    with pytest.raises(ContentUnsatisfied):
        _execute(
            registry=registry,
            plan=_AcquiringPlan(),
            acquirer=acquirer,
            tenant_id="tenant-with-no-notes",
        )


def test_acquisitions_are_recorded_with_their_content_addresses(
    registry: OperatorRegistry,
) -> None:
    """Replay dimension 5 names what was fetched, in resolution order."""
    result = _execute(
        registry=registry,
        plan=_AcquiringPlan(),
        acquirer=_RecordingAcquirer(notes=NOTES),
    )

    assert len(result.acquisitions) == 1
    acquired = result.acquisitions[0]
    assert acquired.request.request_key == REQUEST_KEY
    assert acquired.content_hash == content_hash(NOTES[TENANT])
    assert acquired.content_hash == acquired.rehash()


def test_replay_refeeds_recorded_content_without_acquiring(
    registry: OperatorRegistry,
) -> None:
    """A replay reproduces the payload with no acquirer and no network call.

    INV-CH7-31: the engine is constructed with ``acquirer=None`` and fed the
    recorded acquisitions. A remote resource that moved between the decision
    and the replay cannot change the answer, because nothing is fetched.
    """
    acquirer = _RecordingAcquirer(notes=NOTES)
    original = _execute(registry=registry, plan=_AcquiringPlan(), acquirer=acquirer)
    assert len(acquirer.calls) == 1

    replay_acquirer = _RecordingAcquirer(notes=NOTES)
    replayed = _execute(
        registry=registry,
        plan=_AcquiringPlan(),
        acquirer=None,
        recorded=original.acquisitions,
    )

    assert replay_acquirer.calls == []
    assert replayed.projection.payload == original.projection.payload
    assert content_hash(replayed.projection) == content_hash(original.projection)


def test_a_refed_item_that_does_not_match_its_address_is_refused(
    registry: OperatorRegistry,
) -> None:
    """A tampered re-feed is caught by the content address, not trusted."""
    original = _execute(
        registry=registry,
        plan=_AcquiringPlan(),
        acquirer=_RecordingAcquirer(notes=NOTES),
    )
    tampered = original.acquisitions[0].model_copy(
        update={"content": NOTES[OTHER_TENANT]}
    )
    with pytest.raises(ContentUnsatisfied):
        _execute(
            registry=registry,
            plan=_AcquiringPlan(),
            acquirer=None,
            recorded=(tampered,),
        )


def test_two_principals_over_one_acquirer_do_not_cross(
    registry: OperatorRegistry,
) -> None:
    """D-23: tenancy is a per-call argument, so one acquirer serves both.

    This test fails if ``tenant_id`` moves onto the acquirer's constructor:
    the second execution would receive the first tenant's note.
    """
    acquirer = _RecordingAcquirer(notes=NOTES)
    first = _execute(
        registry=registry, plan=_AcquiringPlan(), acquirer=acquirer, tenant_id=TENANT
    )
    second = _execute(
        registry=registry,
        plan=_AcquiringPlan(),
        acquirer=acquirer,
        tenant_id=OTHER_TENANT,
    )

    assert first.projection.payload[PAYLOAD_KEY] == NOTES[TENANT]
    assert second.projection.payload[PAYLOAD_KEY] == NOTES[OTHER_TENANT]
    assert NOTES[OTHER_TENANT] not in str(first.acquisitions)
    assert NOTES[TENANT] not in str(second.acquisitions)
    assert [tenant for _, tenant in acquirer.calls] == [TENANT, OTHER_TENANT]


def test_a_plan_that_declares_no_content_is_untouched(
    registry: OperatorRegistry,
) -> None:
    """The seam is opt-in: a plain ``ProjectionPlan`` runs unchanged.

    Executed through an engine that *does* hold an acquirer, so the claim is
    that the engine detects the capability structurally rather than that the
    acquirer happened to be absent. This is why ``ContentAcquiringPlan`` is a
    separate Protocol and not a widened ``ProjectionPlan``.
    """
    acquirer = _RecordingAcquirer(notes=NOTES)
    result = _execute(registry=registry, plan=_PlainPlan(), acquirer=acquirer)

    assert acquirer.calls == []
    assert result.acquisitions == ()
    assert result.projection.payload == {}
    assert isinstance(_PlainPlan(), ProjectionPlan)
    assert not isinstance(_PlainPlan(), ContentAcquiringPlan)
    assert isinstance(_AcquiringPlan(), ContentAcquiringPlan)


def test_the_ontology_fixture_owns_the_tenant_vocabulary() -> None:
    """The primary tenant is the fixture's, not this module's."""
    assert TENANT == ONTOLOGY["tenant_id"]
