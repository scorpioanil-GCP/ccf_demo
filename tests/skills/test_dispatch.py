"""Skill dispatch — local_callable, tool and mcp work; a2a is NotYetBound (D-08).

What this suite holds ``src/ccf/skills/dispatch.py`` to:

* a ``local_callable`` entry resolves its ``callable_ref`` as a key in the
  injected ``CallableRegistry`` and invokes what the composition root bound
  there, returning a typed result (D-19 — dispatch imports nothing);
* a ``tool`` entry returns a typed invocation *value* carrying the descriptor
  command and arguments — the SDK ships no execution surface for commands,
  in the same returned-value discipline as ``Agent.emit_effect``;
* an ``mcp`` entry resolves its logical ``{server, resource}`` pair through
  the injected ``McpSkillRegistry`` and reads through the **one shared**
  ``ccf.mcp.client`` — dispatch opens no session and owns no loop of its own
  (D-03, D-IMPL-13) — and every attempt, success or failure, lands on the one
  existing ``AuditLog``;
* an ``a2a`` entry still raises the typed ``NotYetBound`` exception
  (RESEARCH Open Question 2, RESOLVED): the build lacks that transport, and
  nothing about the artifact is bad, which is why this is an exception
  (deployment shape) rather than a returned refusal (bad artifact).

The ``mcp`` cases here use a recording client double rather than a live
server. That is deliberate and it is what makes the *zero network calls*
assertions falsifiable — a real server cannot testify that it was never
contacted. The live proof is ``tests/crossproc/test_mcp_ingress.py``.

All binding values, arguments, and expected outputs live in the skills
fixtures (§6.4); the fixture callable is bound to the entry's declared key by
the ``callable_registry`` fixture in ``tests/conftest.py``, which stands in for
a deployment's composition root (D-19 / D-IMPL-54).
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition
from ccf.agents.errors import NotYetBound
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.mcp.client import McpResourceClient
from ccf.mcp.errors import McpServerUnreachable
from ccf.skills.catalog import (
    SKILL_CATALOG_ENTRY,
    SkillCatalog,
    SkillCatalogEntry,
    skill_catalog_key,
)
from ccf.skills.callables import CallableRegistry
from ccf.skills.dispatch import (
    McpInvocation,
    McpSkillRegistry,
    McpSkillUnregistered,
    SkillInvocation,
    ToolInvocation,
    dispatch_skill,
)
from ccf.skills.grants import (
    GrantLedger,
    RequirementsExceedRegime,
    SkillGrant,
)

from skills.sinks import ScriptedApprovalSink

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking" / "skills"


def _tool_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "covenant_metrics_tool.yaml").read_text()
    )
    return loaded


def _grants_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "grants.yaml").read_text()
    )
    return loaded


def _mcp_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "document_fetch_mcp.yaml").read_text()
    )
    return loaded


def _entry(document: dict[str, Any]) -> SkillCatalogEntry:
    parsed = parse_artifact(document, SKILL_CATALOG_ENTRY)
    assert isinstance(parsed, SkillCatalogEntry)
    return parsed


def test_a_local_callable_entry_resolves_and_invokes_with_typed_arguments(
    callable_registry: CallableRegistry,
) -> None:
    fixture = _tool_fixture()
    entry = _entry(fixture["variants"]["local_callable"])
    result = dispatch_skill(
        entry,
        arguments=fixture["dispatch"]["arguments"],
        callable_registry=callable_registry,
    )
    assert isinstance(result, SkillInvocation)
    assert result.skill_name == entry.name
    assert result.skill_type == "local_callable"
    assert dict(result.output) == fixture["dispatch"]["expected_output"]


def test_a_tool_entry_returns_the_typed_invocation_value(
    callable_registry: CallableRegistry,
) -> None:
    """The invocation is a value the deployment carries onward — the SDK
    executes no command (mechanism, not an execution surface)."""
    fixture = _tool_fixture()
    entry = _entry(fixture["entry"])
    result = dispatch_skill(
        entry,
        arguments=fixture["dispatch"]["arguments"],
        callable_registry=callable_registry,
    )
    assert isinstance(result, ToolInvocation)
    assert result.skill_name == entry.name
    assert result.command == fixture["entry"]["binding"]["command"]
    assert dict(result.arguments) == fixture["dispatch"]["arguments"]


class _RecordingClient(McpResourceClient):
    """A client that answers from the fixture and counts every read.

    Substituted for a live server because the load-bearing assertions here are
    about calls that must *not* happen, and a real server cannot testify to
    its own silence. The live proof is ``tests/crossproc/test_mcp_ingress.py``.
    """

    def __init__(self, *, contents: str) -> None:
        super().__init__(url=_UNUSED_URL)
        self._contents = contents
        self.reads: list[str] = []

    def read_text(self, uri: str) -> str:
        self.reads.append(uri)
        return self._contents


class _UnreachableClient(McpResourceClient):
    """A client whose reads always fail, for the failure-audit case."""

    def __init__(self) -> None:
        super().__init__(url=_UNUSED_URL)
        self.reads: list[str] = []

    def read_text(self, uri: str) -> str:
        self.reads.append(uri)
        raise McpServerUnreachable("fixture server is down")


#: Never dialled: both doubles override ``read_text``, so no transport code
#: ever sees this. Present only because the base class requires an endpoint,
#: and named so a future reader does not mistake it for a real address.
_UNUSED_URL = "unused://never-dialled"


@pytest.fixture
def mcp_world() -> tuple[McpSkillRegistry, _RecordingClient, AuditLog]:
    """A registry wired from the fixture's ``deployment`` block, plus its log.

    The clock is injected and fixed, as everywhere else in the fabric: an
    audit record whose timestamp came from a wall clock does not replay.
    """
    fixture = _mcp_fixture()
    client = _RecordingClient(contents=fixture["dispatch"]["contents"])
    audit = AuditLog()
    registry = McpSkillRegistry(audit_log=audit, clock=lambda: _INSTANT)
    registry.register(
        server=fixture["deployment"]["server"],
        client=client,
        resources=fixture["deployment"]["resources"],
    )
    return registry, client, audit


#: The fixed instant every audit record in this module carries.
_INSTANT = datetime(2026, 1, 1, tzinfo=UTC)


def test_an_mcp_entry_dispatches_through_the_shared_client(
    callable_registry: CallableRegistry,
    mcp_world: tuple[McpSkillRegistry, _RecordingClient, AuditLog],
) -> None:
    """The binding's logical names resolve to the deployment's registered URI.

    The read lands on the URI the *deployment* registered, not on anything
    spelled in the skill artifact — which is the whole SSRF posture in one
    assertion (T-06-24).
    """
    fixture = _mcp_fixture()
    registry, client, _audit = mcp_world
    entry = _entry(fixture["entry"])

    result = dispatch_skill(
        entry,
        arguments=fixture["dispatch"]["arguments"],
        callable_registry=callable_registry,
        mcp_skills=registry,
    )

    assert isinstance(result, McpInvocation)
    assert result.skill_name == entry.name
    assert result.skill_type == "mcp"
    assert result.server == fixture["entry"]["binding"]["server"]
    assert result.resource == fixture["entry"]["binding"]["resource"]
    assert result.contents == fixture["dispatch"]["contents"]
    assert dict(result.arguments) == fixture["dispatch"]["arguments"]
    assert client.reads == [
        fixture["deployment"]["resources"][fixture["entry"]["binding"]["resource"]]
    ]


def test_an_mcp_invocation_lands_in_the_audit_log(
    callable_registry: CallableRegistry,
    mcp_world: tuple[McpSkillRegistry, _RecordingClient, AuditLog],
) -> None:
    """Audit-by-construction: the one existing log, the one existing append.

    The record names the entry's Control Plane key and its exact
    ``artifact_version``, which is what makes "which skill version did this
    decision run against" answerable from the log alone (CLAUDE.md §6.2).
    """
    fixture = _mcp_fixture()
    registry, _client, audit = mcp_world
    entry = _entry(fixture["entry"])

    dispatch_skill(
        entry,
        arguments=fixture["dispatch"]["arguments"],
        callable_registry=callable_registry,
        mcp_skills=registry,
    )

    (event,) = audit.events()
    assert event.action == "skill_invoked"
    assert event.key == skill_catalog_key(entry)
    assert event.version == entry.artifact_version
    assert event.resolved is True
    assert event.occurred_at == _INSTANT
    # The SDK synthesizes no identity (D-IMPL-21).
    assert event.actor is None


def test_a_failed_mcp_invocation_is_audited_as_unresolved(
    callable_registry: CallableRegistry,
) -> None:
    """A log of successes cannot answer "what did this agent fail to reach?".

    Without this record an outage is invisible to the audit plane, which is
    exactly the question a fail-closed posture makes material.
    """
    fixture = _mcp_fixture()
    audit = AuditLog()
    registry = McpSkillRegistry(audit_log=audit, clock=lambda: _INSTANT)
    registry.register(
        server=fixture["deployment"]["server"],
        client=_UnreachableClient(),
        resources=fixture["deployment"]["resources"],
    )
    entry = _entry(fixture["entry"])

    with pytest.raises(McpServerUnreachable):
        dispatch_skill(
            entry,
            arguments={},
            callable_registry=callable_registry,
            mcp_skills=registry,
        )

    (event,) = audit.events()
    assert event.action == "skill_invoked"
    assert event.resolved is False


def test_an_unregistered_resource_is_refused_before_any_read(
    callable_registry: CallableRegistry,
    mcp_world: tuple[McpSkillRegistry, _RecordingClient, AuditLog],
) -> None:
    """A binding can only select among what the composition root offered.

    The count assertion is the point: resolution fails *before* the client is
    touched, so an artifact naming a resource this deployment never registered
    costs no traffic (T-06-24).
    """
    fixture = _mcp_fixture()
    registry, client, _audit = mcp_world
    document = dict(fixture["entry"])
    document["binding"] = {
        "server": fixture["deployment"]["server"],
        "resource": fixture["deployment"]["unregistered_resource"],
    }

    with pytest.raises(McpSkillUnregistered):
        dispatch_skill(
            _entry(document),
            arguments={},
            callable_registry=callable_registry,
            mcp_skills=registry,
        )

    assert client.reads == []


def test_dispatch_without_a_registry_refuses_rather_than_improvising(
    callable_registry: CallableRegistry,
) -> None:
    """No client is manufactured behind the deployment's back.

    Constructing one here would mean the SDK choosing an endpoint, which is
    the one thing CINV-01 says it never does.
    """
    entry = _entry(_mcp_fixture()["entry"])
    with pytest.raises(McpSkillUnregistered):
        dispatch_skill(entry, arguments={}, callable_registry=callable_registry)


def test_no_public_dispatch_entry_point_accepts_a_server_address() -> None:
    """The SSRF control, asserted on the surface rather than on behaviour.

    Shape is what enforces it: if no parameter can carry an address, a fetched
    payload has no channel through which to steer the next fetch. A behavioural
    test would only prove that today's callers do not pass one.
    """
    forbidden = {"url", "endpoint", "server", "host", "uri", "address"}
    surfaces: list[Any] = [dispatch_skill, McpSkillRegistry.resolve]
    for surface in surfaces:
        taken = set(inspect.signature(surface).parameters) & forbidden
        assert not taken, (
            f"{surface.__qualname__} accepts {sorted(taken)} at call time; "
            "addresses come from Control Plane configuration at registration "
            "(T-06-24)"
        )
    # Registration is where an address legitimately arrives — and it takes a
    # *client*, so even there the endpoint is one the composition root built.
    assert "url" not in inspect.signature(McpSkillRegistry.register).parameters


def test_an_ungranted_mcp_skill_is_refused_with_zero_network_calls() -> None:
    """Governance runs ahead of the network, through the real grant machinery.

    The mcp entry requires a scope the ``auto`` regime does not permit, so
    tier 1 returns a refusal, the bound view stays empty, and dispatch is
    never reached. The recording client proves the last part: had the order
    been the other way round, the read would already have happened.
    """
    mcp = _mcp_fixture()
    grants = _grants_fixture()
    instant = datetime.fromisoformat(grants["clock"]["start"])

    audit = AuditLog()
    control = ControlPlaneRegistry(clock=lambda: instant, audit_log=audit)
    regime = grants["policy_regimes"]["auto"]
    artifact_class = declared_artifact_class(regime["class_id"])
    control.register_typed(
        regime["key"],
        parse_artifact(
            {
                "class_id": regime["class_id"],
                "semver": regime["semver"],
                "declaration": regime["declaration"],
            },
            artifact_class,
        ),
        artifact_class,
    )
    catalog = SkillCatalog(control)
    entry = _entry(mcp["entry"])
    assert isinstance(catalog.register(entry), str)

    definition = parse_artifact(grants["agents"]["auto"], AGENT_DEFINITION)
    assert isinstance(definition, AgentDefinition)
    ledger = GrantLedger(
        control_plane=control,
        catalog=catalog,
        audit=audit,
        sink=ScriptedApprovalSink(
            approve=True, approver_id=grants["approval"]["approver_id"]
        ),
        clock=lambda: instant,
    )

    client = _RecordingClient(contents=mcp["dispatch"]["contents"])
    registry = McpSkillRegistry(audit_log=audit, clock=lambda: instant)
    registry.register(
        server=mcp["deployment"]["server"],
        client=client,
        resources=mcp["deployment"]["resources"],
    )

    outcome = ledger.request(
        SkillGrant(
            agent_definition_hash=content_hash(definition),
            **mcp["grant"],
        ),
        definition=definition,
        actor=grants["approval"]["requesting_actor"],
    )

    assert isinstance(outcome, RequirementsExceedRegime)
    assert set(outcome.excess_scopes) == set(mcp["expected_excess_scopes"])
    # The skill does not exist from the agent's surface, so there is nothing
    # to dispatch — and nothing was contacted on the way to finding that out.
    assert entry.name not in ledger.bound_view(content_hash(definition))
    assert client.reads == []


def test_an_a2a_entry_raises_exactly_not_yet_bound(
    callable_registry: CallableRegistry,
) -> None:
    entry = _entry(_tool_fixture()["variants"]["a2a"])
    with pytest.raises(NotYetBound) as excinfo:
        dispatch_skill(entry, arguments={}, callable_registry=callable_registry)
    assert type(excinfo.value) is NotYetBound


def test_not_yet_bound_is_a_typed_exception_not_a_refusal_value() -> None:
    """The refusal-vs-exception line, documented side: a granted, valid
    artifact whose transport this build lacks is a deployment-shape fact."""
    assert issubclass(NotYetBound, RuntimeError)
