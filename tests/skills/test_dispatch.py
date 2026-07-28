"""Skill dispatch — all four skill types, and the tail that survives them (D-08).

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
* an ``a2a`` entry resolves its logical ``endpoint`` through the injected
  ``A2ASkillRegistry`` to a **``PeeringProtocol``** — the abstraction, never a
  concrete transport — reads what that transport received, lands on the same
  one ``AuditLog``, and returns values that are *unadmitted* and unadmittable
  from there (D-12: the Control Plane gate stays above every transport);
* the ``NotYetBound`` tail survives all four being bound, for a fifth skill
  type a later artifact schema introduces — and its message no longer names
  MCP or A2A as outstanding, which is asserted rather than reviewed.

The ``mcp`` and ``a2a`` cases here use recording doubles rather than a live
server or peer. That is deliberate and it is what makes the *zero network
calls* assertions falsifiable — a real server cannot testify that it was never
contacted. The live proofs are ``tests/crossproc/test_mcp_ingress.py`` and
``tests/crossproc/test_peering_exchange.py``, the latter over both wires.

All binding values, arguments, and expected outputs live in the skills
fixtures (§6.4); the fixture callable is bound to the entry's declared key by
the ``callable_registry`` fixture in ``tests/conftest.py``, which stands in for
a deployment's composition root (D-19 / D-IMPL-54).
"""

from __future__ import annotations

import ast
import inspect
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.peering.admission import AdmittedProduct
from ccf.peering.identity import SignedContextProduct
from ccf.peering.protocol import EmitReceipt, InboundProduct, PeerRef, PeeringProtocol
from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition
from ccf.agents.errors import NotYetBound
from ccf.contracts.base import CCFContract
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
    A2AInvocation,
    A2ASkillRegistry,
    A2ASkillUnregistered,
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

from ccf_runtime.peering.typed_http import PeerUnreachable

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


def _a2a_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "remote_products_a2a.yaml").read_text()
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
    surfaces: list[Any] = [
        dispatch_skill,
        McpSkillRegistry.resolve,
        A2ASkillRegistry.resolve,
    ]
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
    # The A2A registry goes one better: it takes no address at registration
    # either, only a name and an already-wired transport, so the address lives
    # one level further from the artifact than MCP's does (T-06-57).
    a2a_register = set(inspect.signature(A2ASkillRegistry.register).parameters)
    assert a2a_register & forbidden == {"endpoint"}
    assert "transport" in a2a_register


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


# --- a2a (D-08, the fourth and last transport) -------------------------------


class _RecordingWire:
    """A ``PeeringProtocol`` double that answers from the fixture and counts calls.

    Substituted for a live transport because the load-bearing assertions here
    are about calls that must *not* happen, and a real transport cannot testify
    to its own silence. The live proof — a genuinely signed product crossing a
    real process boundary over both wires — is
    ``tests/crossproc/test_peering_exchange.py``.

    It implements the abstraction, not either shipped transport. That is the
    assertion by construction: if ``dispatch_skill`` had typed against
    ``TypedHttpWire`` or ``LfA2AWire``, this double could not be substituted and
    ``/src`` would have grown a transport dependency.
    """

    def __init__(self, *, products: tuple[InboundProduct, ...] = ()) -> None:
        self._products = products
        self.emits: list[PeerRef] = []
        self.receives = 0

    def emit(
        self, *, peer: PeerRef, signed: SignedContextProduct
    ) -> EmitReceipt:
        self.emits.append(peer)
        raise AssertionError("dispatch must not emit")

    def receive(self) -> Iterator[InboundProduct]:
        self.receives += 1
        yield from self._products

    @property
    def calls(self) -> int:
        """Every call that would have touched the network, of either kind."""
        return self.receives + len(self.emits)


class _FailingWire(_RecordingWire):
    """A transport whose reads always fail, for the failure-audit case."""

    def receive(self) -> Iterator[InboundProduct]:
        self.receives += 1
        raise PeerUnreachable("fixture peer is down")
        yield  # pragma: no cover - unreachable, present to keep this a generator


def _inbound(declared: dict[str, Any]) -> InboundProduct:
    return InboundProduct(
        observed_peer=PeerRef(
            tenant_id=declared["tenant_id"], peer_id=declared["peer_id"]
        ),
        signed=SignedContextProduct(
            payload=declared["payload"],
            protected=declared["protected"],
            signature=declared["signature"],
        ),
    )


@pytest.fixture
def a2a_world() -> tuple[A2ASkillRegistry, _RecordingWire, AuditLog]:
    """A registry wired from the fixture's ``deployment`` block, plus its log."""
    fixture = _a2a_fixture()
    wire = _RecordingWire(products=(_inbound(fixture["inbound"]),))
    audit = AuditLog()
    registry = A2ASkillRegistry(audit_log=audit, clock=lambda: _INSTANT)
    registry.register(
        endpoint=fixture["deployment"]["endpoint"], transport=wire
    )
    return registry, wire, audit


def test_an_a2a_entry_dispatches_through_the_wire_protocol(
    callable_registry: CallableRegistry,
    a2a_world: tuple[A2ASkillRegistry, _RecordingWire, AuditLog],
) -> None:
    """The binding's logical endpoint name resolves to a registered transport.

    What would fail here: dispatch that treated ``binding.endpoint`` as an
    address to dial. The registered name and the artifact's name are the same
    string precisely so that a *different* string — the fixture's
    ``unregistered_endpoint``, written as a URL — has nowhere to go (T-06-57).
    """
    fixture = _a2a_fixture()
    registry, wire, _audit = a2a_world
    entry = _entry(fixture["entry"])

    result = dispatch_skill(
        entry,
        arguments=fixture["dispatch"]["arguments"],
        callable_registry=callable_registry,
        a2a_skills=registry,
    )

    assert isinstance(result, A2AInvocation)
    assert result.skill_name == entry.name
    assert result.skill_type == "a2a"
    assert result.endpoint == fixture["entry"]["binding"]["endpoint"]
    assert dict(result.arguments) == fixture["dispatch"]["arguments"]
    assert wire.receives == 1
    assert wire.emits == []

    (product,) = result.products
    assert product.observed_peer.peer_id == fixture["inbound"]["peer_id"]
    # Unadmitted, and unadmittable from here: what comes back is an
    # ``InboundProduct``, which L2 does not accept, and dispatch cannot build
    # the ``AdmittedProduct`` it would (D-12).
    assert not isinstance(product, AdmittedProduct)


def test_dispatch_imports_no_transport_no_runtime_and_no_protobuf() -> None:
    """``/src`` acquires nothing from a wire by binding the fourth type.

    An AST import scan, not a source-text grep. A grep cannot tell an import
    from a docstring naming the thing not imported — and this module's docstring
    does name both shipped wires, in the course of explaining that it depends on
    neither. An import is an ``ast.Import``; a mention is an ``ast.Constant``,
    which this cannot see.

    What would fail here: dispatch reaching for a concrete transport "just to
    type the parameter". That is how ``/src`` grows an ``httpx`` and then a
    protobuf dependency, and how the D-IMPL-14 wire stops being replaceable.
    """
    import ccf.skills.dispatch as module  # noqa: PLC0415

    imported: set[str] = set()
    for node in ast.walk(ast.parse(inspect.getsource(module))):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    assert imported, "the scan found no imports; it would pass vacuously"
    forbidden = ("ccf_runtime", "httpx", "a2a.", "a2a_pb2", "google.protobuf")
    offending = sorted(
        name
        for name in imported
        # `ccf.peering.protocol` is the abstraction and is exactly what this module
        # *should* import; the prefixes below are transports and vendor wire
        # types, which it must not.
        if name.startswith(forbidden) or name in {"a2a", "protobuf"}
    )
    assert not offending, offending
    assert "ccf.peering.protocol" in imported


def test_dispatch_types_against_the_protocol_not_a_concrete_transport(
    a2a_world: tuple[A2ASkillRegistry, _RecordingWire, AuditLog],
) -> None:
    """CLAUDE.md §7.2: the Contract is the stable layer, the wire replaceable.

    What would fail here: a registry that accepted only a shipped transport.
    The double satisfies the Protocol and nothing else, so its acceptance above
    *is* the statement that either wire — or a third — binds at the composition
    root without ``/src`` changing.
    """
    _registry, wire, _audit = a2a_world
    assert isinstance(wire, PeeringProtocol)


def test_an_a2a_invocation_lands_in_the_audit_log(
    callable_registry: CallableRegistry,
    a2a_world: tuple[A2ASkillRegistry, _RecordingWire, AuditLog],
) -> None:
    """Audit-by-construction on the *one* existing log, not a parallel one.

    Same action, same shape and same key discipline as the ``mcp`` path
    (T-06-59): "which skills did this agent invoke, at which artifact version"
    must be answerable from one query.
    """
    fixture = _a2a_fixture()
    registry, _wire, audit = a2a_world
    entry = _entry(fixture["entry"])

    dispatch_skill(
        entry,
        arguments=fixture["dispatch"]["arguments"],
        callable_registry=callable_registry,
        a2a_skills=registry,
    )

    (event,) = audit.events()
    assert event.action == "skill_invoked"
    assert event.key == skill_catalog_key(entry)
    assert event.version == entry.artifact_version
    assert event.resolved is True
    assert event.occurred_at == _INSTANT
    assert event.actor is None


def test_a_failed_a2a_invocation_is_audited_as_unresolved(
    callable_registry: CallableRegistry,
) -> None:
    """An unreachable peer is visible to the audit plane, not just to a caller."""
    fixture = _a2a_fixture()
    audit = AuditLog()
    registry = A2ASkillRegistry(audit_log=audit, clock=lambda: _INSTANT)
    registry.register(
        endpoint=fixture["deployment"]["endpoint"], transport=_FailingWire()
    )
    entry = _entry(fixture["entry"])

    with pytest.raises(PeerUnreachable):
        dispatch_skill(
            entry,
            arguments={},
            callable_registry=callable_registry,
            a2a_skills=registry,
        )

    (event,) = audit.events()
    assert event.action == "skill_invoked"
    assert event.resolved is False


def test_an_unregistered_a2a_endpoint_is_refused_before_any_call(
    callable_registry: CallableRegistry,
    a2a_world: tuple[A2ASkillRegistry, _RecordingWire, AuditLog],
) -> None:
    """A URL-shaped artifact value buys an attacker nothing (T-06-57).

    The fixture's unregistered endpoint is spelled as a real-looking URL on
    purpose. It is matched as a *name*, resolves to no registration, and the
    call count proves nothing was dialled on the way to finding that out.
    """
    fixture = _a2a_fixture()
    registry, wire, _audit = a2a_world
    document = dict(fixture["entry"])
    document["binding"] = {
        "endpoint": fixture["deployment"]["unregistered_endpoint"]
    }

    with pytest.raises(A2ASkillUnregistered):
        dispatch_skill(
            _entry(document),
            arguments={},
            callable_registry=callable_registry,
            a2a_skills=registry,
        )

    assert wire.calls == 0


def test_a2a_dispatch_without_a_registry_refuses_rather_than_improvising(
    callable_registry: CallableRegistry,
) -> None:
    """No transport is manufactured behind the deployment's back (CINV-01)."""
    entry = _entry(_a2a_fixture()["entry"])
    with pytest.raises(A2ASkillUnregistered):
        dispatch_skill(entry, arguments={}, callable_registry=callable_registry)


def test_an_ungranted_a2a_skill_is_refused_with_zero_network_calls() -> None:
    """Governance runs ahead of the network, through the real grant machinery.

    T-06-58. The entry requires a scope the ``auto`` regime does not permit, so
    tier 1 returns a refusal, the bound view stays empty, and dispatch is never
    reached. The recording transport proves the last part: had the order been
    the other way round, ``receive`` would already have run.
    """
    fixture = _a2a_fixture()
    denied = fixture["denied"]
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
    entry = _entry(denied["entry"])
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

    wire = _RecordingWire()
    registry = A2ASkillRegistry(audit_log=audit, clock=lambda: instant)
    registry.register(
        endpoint=fixture["deployment"]["endpoint"], transport=wire
    )

    outcome = ledger.request(
        SkillGrant(
            agent_definition_hash=content_hash(definition),
            **denied["grant"],
        ),
        definition=definition,
        actor=grants["approval"]["requesting_actor"],
    )

    assert isinstance(outcome, RequirementsExceedRegime)
    assert set(outcome.excess_scopes) == set(denied["expected_excess_scopes"])
    # The skill does not exist from the agent's surface, so there is nothing to
    # dispatch — and nothing was contacted on the way to finding that out.
    assert entry.name not in ledger.bound_view(content_hash(definition))
    assert wire.calls == 0


# --- the tail ----------------------------------------------------------------


def test_an_unrecognized_skill_type_still_raises_not_yet_bound(
    callable_registry: CallableRegistry,
) -> None:
    """The ``NotYetBound`` tail survives all four transports being bound.

    Constructed with ``model_construct`` because no *artifact* can currently
    reach this branch — :class:`SkillCatalogEntry` validates a binding against
    its declared type — and that is exactly why the branch is worth pinning: it
    exists for a fifth skill type a later artifact schema introduces, and the
    only way to test today's behaviour under tomorrow's input is to bypass the
    validation that has not yet been widened. Without this case, deleting the
    tail would look free.
    """

    class _FutureBinding(CCFContract):
        detail: str

    entry = SkillCatalogEntry.model_construct(
        schema_version="1.0.0",
        artifact_version="1.0.0",
        name="a-later-skill-type",
        tenant="acme-bank",
        skill_type="not-a-shipped-type",
        binding=_FutureBinding(detail="unbound"),
    )

    with pytest.raises(NotYetBound) as excinfo:
        dispatch_skill(entry, arguments={}, callable_registry=callable_registry)
    assert type(excinfo.value) is NotYetBound


def test_the_not_yet_bound_message_names_no_outstanding_transport() -> None:
    """All four types dispatch, so the tail must not still claim otherwise.

    A message naming MCP or A2A as outstanding would be false, and a false
    error message is how a reader concludes a working path is unimplemented.
    """
    source = inspect.getsource(dispatch_skill)
    tail = source[source.index("raise NotYetBound") :]
    assert "A2A" not in tail
    assert "MCP" not in tail
    assert "mcp" not in tail


def test_not_yet_bound_is_a_typed_exception_not_a_refusal_value() -> None:
    """The refusal-vs-exception line, documented side: a granted, valid
    artifact whose dispatch path this build lacks is a deployment-shape fact."""
    assert issubclass(NotYetBound, RuntimeError)
