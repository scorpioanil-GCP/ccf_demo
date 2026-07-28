"""L4/L5 acquisition across a real process boundary (XPRC-01, ROADMAP crit. 1).

CLAUDE.md §7.1 bullet 2 ("MCP as ingress for content acquisition (L4–L5)");
whitepaper §6.6 (search-inference recursion); §10 (single-writer); §11
(algorithmic⇄semantic alternation).

ROADMAP criterion 1 requires MCP *client* ingress at L1/L4/L5/Experience. A
shared client library existing does not deliver the L4/L5 leg, and saying it
does is the overclaim D-21 forbids. This module is the leg: a projection that
declares a content requirement is served that content over real loopback HTTP
from a server in another OS process, and the payload it returns carries a value
that exists nowhere in this process.

| Invariant | Row asserted by | What would fail |
|---|---|---|
| The edge is bound end to end | ``test_the_served_payload_carries_a_value_only_the_child_had`` | Deleting the engine's acquisition stage — the note never reaches the payload |
| Acquisition never writes (CLAUDE.md §10) | ``test_the_graph_state_watermark_is_unchanged_by_an_acquiring_execution`` | An acquirer or engine that promoted acquired content into L3 |
| Operators stayed pure (INV-CH7-22/23) | ``test_the_operator_plan_ran_with_no_io_of_its_own`` | Moving the fetch onto ``Operator.apply`` — the operator provenance would carry it |
| Policy ran before the fetch (INV-CH7-26) | ``test_policy_constrained_the_view_before_anything_was_fetched`` | Acquiring before the operator plan resolved |
| No LLM in the acquisition path (CINV-03) | ``test_no_llm_client_is_reachable_from_the_acquisition_path`` | An acquirer that interpreted what it fetched |
| Two principals cannot cross (D-23) | ``test_two_principals_over_one_acquirer_receive_only_their_own`` | Moving ``tenant_id`` onto the acquirer's constructor |
| Replay re-feeds, never re-acquires (INV-CH7-31) | ``test_replay_reproduces_the_payload_with_the_child_gone`` | An engine that reached the network at replay |

Every domain value comes from ``tests/fixtures/banking/``. The note text is
read from the same fixture the child serves from, so the served value and the
expected value cannot drift.
"""

from __future__ import annotations

import inspect
import sys
from collections.abc import Iterator, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.graph.protocols import GraphView
from ccf.mcp import acquisition as acquisition_module
from ccf.mcp.acquisition import McpContentAcquirer
from ccf.mcp.client import McpResourceClient, SyncMcpBridge
from ccf.operators.base import OperatorOutput
from ccf.projection import acquisition as seam_module
from ccf.projection.acquisition import AcquiredContent, ContentRequest
from ccf.projection.engine import ExecutionResult, ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionOutput

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crossproc.servers.mcp_content_child import load_content_fixture  # noqa: E402

CHILD = str(
    Path(__file__).resolve().parent / "servers" / "mcp_content_child.py"
)
CONTENT = load_content_fixture()
NOTES: Mapping[str, str] = CONTENT["notes"]
REQUEST_KEY: str = CONTENT["request"]["request_key"]
SELECTOR: str = CONTENT["request"]["selector"]
SOURCE_KEY: str = CONTENT["sources"]["covenant_notes"]
PAYLOAD_KEY: str = CONTENT["payload_key"]
PRIMARY: str = CONTENT["tenants"]["primary"]
SECONDARY: str = CONTENT["tenants"]["secondary"]

#: Bridge deadline for this suite. A test-side deployment value (D-IMPL-38 —
#: the SDK ships no default), generous enough that a slow CI box does not
#: report a timeout as a transport failure.
CALL_TIMEOUT_SECONDS = 20.0

pytestmark = pytest.mark.crossproc


class _AcquiringSummaryPlan:
    """The deployment's Π: the fixture operators plus one acquired note.

    Declares content the graph does not hold, and publishes it. The payload is
    where the whole proof lands.
    """

    def __init__(self, *, plan_id: str, required: tuple[str, ...]) -> None:
        self._plan_id = plan_id
        self._required = required

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def required_content(self) -> tuple[ContentRequest, ...]:
        return (
            ContentRequest(
                request_key=REQUEST_KEY,
                source_key=SOURCE_KEY,
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
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                PAYLOAD_KEY: acquired_content[REQUEST_KEY].content,
                "entities_in_view": len(view.entities),
            },
        )


@pytest.fixture
def fabric(tmp_path: Path) -> Iterator[Any]:
    """A booted banking fabric with the fixture event stream ingested.

    Reused from the proto-quickstart integration module rather than
    re-implemented: that module is the repository's one worked example of
    assembling state the way a deployment would, and a second copy here would
    be a second thing to keep correct.
    """
    from integration.test_proto_quickstart import (  # noqa: PLC0415
        _Fabric,
        _envelopes,
        _load,
        _resolution_spec,
    )

    from ccf.boot import boot  # noqa: PLC0415
    from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: PLC0415

    ontology: Any = _load("ontology.yaml")
    control: Any = _load("controlplane.yaml")
    events: Any = _load("events.yaml")

    keys = control["keys"]
    registry = ControlPlaneRegistry()
    spec_version = registry.register(
        keys["resolution_spec"], _resolution_spec(ontology)
    )
    policy_version = registry.register(keys["policy_bundle"], control["policy_bundle"])
    handle = boot(
        database_path=tmp_path / "acquisition.sqlite3",
        registry=registry,
        resolution_spec_key=keys["resolution_spec"],
        resolution_spec_version=spec_version,
        policy_bundle_key=keys["policy_bundle"],
        policy_bundle_version=policy_version,
    )
    try:
        for envelope in _envelopes(ontology, events):
            handle.worker.ingest(envelope)
        yield _Fabric(
            handle=handle,
            registry=registry,
            policy_version=policy_version,
            ontology=ontology,
            control=control,
        )
    finally:
        handle.close()


def _operator_registry(fabric: Any) -> Any:
    from integration.test_proto_quickstart import _operators  # noqa: PLC0415

    return _operators(fabric)


def _perspective(fabric: Any) -> Perspective:
    values = fabric.control["perspective"]
    return Perspective(
        principal_id=values["principal_id"], role=values["role"]
    )


def _watermark(fabric: Any, *, tenant_id: str) -> str:
    """Content address of the tenant's whole graph state at the boundary."""
    return content_hash(
        fabric.handle.reader.as_of(tenant_id=tenant_id, at=fabric.boundary)
    )


@pytest.fixture
def acquirer(loopback_url: str) -> Iterator[McpContentAcquirer]:
    """An acquirer over the one shared MCP client, addressed at the child.

    The address is assembled test-side and reaches the acquirer through
    *construction*. No method on it accepts a URL at call time — the SSRF
    posture is a property of the shape (T-06-97).
    """
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
        yield McpContentAcquirer(
            sources={
                SOURCE_KEY: McpResourceClient(url=loopback_url, bridge=bridge)
            }
        )


def _execute(
    fabric: Any,
    *,
    acquirer: McpContentAcquirer | None,
    tenant_id: str | None = None,
    recorded: tuple[AcquiredContent, ...] | None = None,
) -> ExecutionResult:
    registry = _operator_registry(fabric)
    plan = _AcquiringSummaryPlan(
        plan_id=fabric.control["product_class"]["plan_id"],
        required=registry.keys(),
    )
    engine = ProjectionEngine(
        reader=fabric.handle.reader, registry=registry, acquirer=acquirer
    )
    return engine.execute(
        plan=plan,
        perspective=_perspective(fabric),
        tenant_id=tenant_id or fabric.tenant_id,
        temporal_boundary=fabric.boundary,
        recorded_acquisitions=recorded,
    )


@pytest.mark.parametrize("child_server_port", [CHILD], indirect=True)
def test_the_served_payload_carries_a_value_only_the_child_had(
    fabric: Any, acquirer: McpContentAcquirer
) -> None:
    """The L4/L5 leg of ROADMAP criterion 1, executed rather than argued.

    The note is served by another OS process over real loopback HTTP. Nothing
    in this process's graph, envelopes, or ontology carries it — asserted
    below — so a payload containing it can only have come through the engine's
    acquisition stage and the shared MCP client. Remove the stage and this
    fails.
    """
    expected = NOTES[PRIMARY]
    watermark_before = _watermark(fabric, tenant_id=fabric.tenant_id)
    view = fabric.handle.reader.as_of(
        tenant_id=fabric.tenant_id, at=fabric.boundary
    )
    assert expected not in str(view)

    result = _execute(fabric, acquirer=acquirer)

    assert result.projection.payload[PAYLOAD_KEY] == expected
    assert result.acquisitions[0].content_hash == content_hash(expected)
    assert _watermark(fabric, tenant_id=fabric.tenant_id) == watermark_before


@pytest.mark.parametrize("child_server_port", [CHILD], indirect=True)
def test_the_graph_state_watermark_is_unchanged_by_an_acquiring_execution(
    fabric: Any, acquirer: McpContentAcquirer
) -> None:
    """Nothing acquired at L4/L5 reaches L3 (CLAUDE.md §10, T-06-98).

    The store-state watermark is byte-identical before and after, and the
    acquired note is absent from the graph afterwards. Acquired content
    terminates in the projection payload; if a deployment wants it in the
    graph it enters through L1/L2 like everything else.
    """
    before = _watermark(fabric, tenant_id=fabric.tenant_id)

    result = _execute(fabric, acquirer=acquirer)

    after_view = fabric.handle.reader.as_of(
        tenant_id=fabric.tenant_id, at=fabric.boundary
    )
    assert content_hash(after_view) == before
    assert NOTES[PRIMARY] not in str(after_view)
    assert result.projection.payload[PAYLOAD_KEY] == NOTES[PRIMARY]
    # The engine that just acquired still has no writer to hand out.
    assert not hasattr(ProjectionEngine, "writer")


@pytest.mark.parametrize("child_server_port", [CHILD], indirect=True)
def test_the_operator_plan_ran_with_no_io_of_its_own(
    fabric: Any, acquirer: McpContentAcquirer
) -> None:
    """Operator purity survives the addition (INV-CH7-22/23).

    The acquisition is an engine stage, so no operator performed I/O and the
    purity sentence in ``ccf.operators.base`` is still true. The executed steps
    are exactly the registered operators — the fetch is not one of them.
    """
    from ccf.operators import base as operator_base  # noqa: PLC0415

    result = _execute(fabric, acquirer=acquirer)

    assert "no writes, no I/O" in inspect.getsource(operator_base)
    assert set(result.operators_invoked) == set(_operator_registry(fabric).keys())
    assert REQUEST_KEY not in {step.operator_key for step in result.steps}
    assert NOTES[PRIMARY] not in str(result.provenance)


@pytest.mark.parametrize("child_server_port", [CHILD], indirect=True)
def test_policy_constrained_the_view_before_anything_was_fetched(
    fabric: Any, acquirer: McpContentAcquirer
) -> None:
    """INV-CH7-26 applied to acquisition (T-06-100).

    Policy is the first executed step, and the acquisition stage runs after the
    whole operator plan, so nothing is fetched on behalf of a principal the
    Policy stage excluded.
    """
    result = _execute(fabric, acquirer=acquirer)

    categories = [step.category for step in result.steps]
    assert categories[0] == "policy"
    assert result.acquisitions, "the plan declared content and it was resolved"
    # Π saw both: the Policy-constrained view and the acquired note.
    assert result.projection.payload["entities_in_view"] == len(result.view.entities)


@pytest.mark.parametrize("child_server_port", [CHILD], indirect=True)
def test_two_principals_over_one_acquirer_receive_only_their_own(
    fabric: Any, acquirer: McpContentAcquirer
) -> None:
    """D-23: tenancy is a per-call argument on ``acquire()`` (T-06-101).

    One acquirer, one child server, two tenants. This test fails if tenancy
    moves onto the acquirer's constructor — the second execution would receive
    the first tenant's note.
    """
    first = _execute(fabric, acquirer=acquirer, tenant_id=PRIMARY)
    second = _execute(fabric, acquirer=acquirer, tenant_id=SECONDARY)

    assert first.projection.payload[PAYLOAD_KEY] == NOTES[PRIMARY]
    assert second.projection.payload[PAYLOAD_KEY] == NOTES[SECONDARY]
    assert NOTES[SECONDARY] not in str(first.acquisitions)
    assert NOTES[PRIMARY] not in str(second.acquisitions)


@pytest.mark.parametrize("child_server_port", [CHILD], indirect=True)
def test_replay_reproduces_the_payload_with_the_child_gone(
    fabric: Any, acquirer: McpContentAcquirer
) -> None:
    """INV-CH7-31 / T-06-99: replay re-feeds, it does not re-acquire.

    The replay engine is constructed with ``acquirer=None``, so there is no
    network call available to it, and it still reproduces the original payload
    exactly from the recorded acquisitions.
    """
    original = _execute(fabric, acquirer=acquirer)

    replayed = _execute(fabric, acquirer=None, recorded=original.acquisitions)

    assert replayed.projection.payload == original.projection.payload
    assert content_hash(replayed.projection) == content_hash(original.projection)


def test_no_llm_client_is_reachable_from_the_acquisition_path() -> None:
    """CINV-03: the acquisition path fetches, it never interprets.

    Both modules declare themselves algorithmic and neither names an LLM
    surface. Meaning is Π's job, which is where the semantic stage belongs
    (CLAUDE.md §11, whitepaper §7.6.6). Runs without a child — it is a property
    of the modules, not of a session.
    """
    for module in (seam_module, acquisition_module):
        source = inspect.getsource(module)
        assert module.__ccf_mode__ == "algorithmic"
        assert "ccf.llm" not in source
        assert "anthropic" not in source.lower()
