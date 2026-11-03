# Copyright (c) 2026 David Castillo. All rights reserved.
"""A current-API adaptation of ccf_code/archive/examples/02-skilling.

Run locally with an authorized installation of the CCF SDK. Identity and
approval fixtures are explicitly simulated; SDK authorization, policy checks,
dispatch, grant state, and auditing are real. See README.md for the boundary.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import yaml

from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition
from ccf.agents.errors import SkillNotBound
from ccf.agents.factory import AgentFactory
from ccf.authz.capability import (
    COMPOSITION_PRINCIPAL, CompositionRegister,
    SkillGrant as SkillGrantAuthority, SkillRevoke, mint, mint_at_composition,
)
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import SkillCatalog, SkillCatalogEntry, skill_catalog_key
from ccf.skills.grants import (
    ApprovalOutcome, GrantLedger, RequirementsExceedRegime, SkillGrant,
)
from ccf.skills.toolsurface import render_tool_surface
from ccf.skills.wire_arguments import ArgumentRefused
from ccf_runtime.authz.artifact import SCOPE_MAPPING, ScopeEntry, ScopeMappingArtifact
from ccf_runtime.authz.protocol import ControlPlaneTenantAuthorizer
from ccf_runtime.mcp.auth import TokenGrant

from calculation import CovenantCalculator

SDK_BASELINE = "5f85b389efe9e4b1de62e84a5af62ca4b2e12178"
SCENARIO = Path(__file__).parent / "artifacts" / "scenario.yaml"


class ScriptedDemoApproval:
    """A visible approval fixture, not an authenticated human approval gate."""

    def __init__(self, approver_id: str, approve: bool) -> None:
        self.approver_id, self.approve = approver_id, approve
        self.requests: list[str] = []

    def decide(self, grant: SkillGrant) -> ApprovalOutcome:
        self.requests.append(grant.name)
        return ApprovalOutcome(approved=self.approve, approver_id=self.approver_id)


class Demo:
    """Trusted local composition root; never expose this constructor as a door."""

    def __init__(self, *, approve: bool = True) -> None:
        self.config = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
        config = self.config
        self.tenant = config["tenant"]
        self.instant = datetime.fromisoformat(config["clock"])
        self.audit = AuditLog()
        self.registry = ControlPlaneRegistry(clock=lambda: self.instant, audit_log=self.audit)
        self.catalog = SkillCatalog(self.registry)

        for item in config["referenced_artifacts"]:
            artifact_class = declared_artifact_class(item["class_id"])
            artifact = parse_artifact({k: v for k, v in item.items() if k != "key"}, artifact_class)
            self.registry.register_typed(self.bootstrap(item["key"]), artifact, artifact_class)
        self.definition = AgentDefinition.model_validate(config["agent_definition"])
        self.definition_hash = content_hash(self.definition)
        definition_version = self.registry.register_versioned(
            self.bootstrap(config["keys"]["agent"]), self.definition, AGENT_DEFINITION
        )
        if not isinstance(definition_version, str):
            raise RuntimeError(f"Agent registration refused: {definition_version}")
        self.entries = {}
        for label, document in config["skills"].items():
            entry = SkillCatalogEntry.model_validate(document)
            outcome = self.catalog.register(self.bootstrap(skill_catalog_key(entry)), entry)
            if not isinstance(outcome, str):
                raise RuntimeError(f"Catalog registration refused: {outcome}")
            self.entries[label] = entry
        self.grants = {
            label: SkillGrant(
                schema_version="1.0.0", artifact_version="1.0.0",
                name=config["grants"][label], tenant=self.tenant,
                agent_definition_hash=self.definition_hash,
                skill_name=entry.name, skill_version=entry.artifact_version,
            ) for label, entry in self.entries.items()
        }
        # Exact resources: the operator can grant to this definition and revoke
        # these demonstration grants. No wildcard authorization is needed.
        scope_mapping = ScopeMappingArtifact(semver="1.0.0", scopes={
            "grant-skills": ScopeEntry(
                tenant_patterns=(self.tenant,), action_ids=(SkillGrantAuthority.action_id,),
                resource_patterns=(config["keys"]["agent"],),
            ),
            "revoke-skills": ScopeEntry(
                tenant_patterns=(self.tenant,), action_ids=(SkillRevoke.action_id,),
                resource_patterns=tuple(content_hash(g) for g in self.grants.values()),
            ),
        })
        scope_key = config["keys"]["scope_mapping"]
        scope_version = self.registry.register_typed(
            self.bootstrap(scope_key), scope_mapping, SCOPE_MAPPING
        )
        self.authorizer = ControlPlaneTenantAuthorizer(
            control_plane=self.registry, scope_mapping_key=scope_key,
            scope_mapping_version=scope_version, clock=lambda: self.instant,
        )
        # Trusted fixture identities stand in for a verified token source.
        # Never accept these claims from an unverified request body.
        self.identities = {
            name: TokenGrant(**values, tenants=frozenset({self.tenant}), products=frozenset())
            for name, values in config["identities"].items()
        }
        self.sink = ScriptedDemoApproval(config["approval"]["approver_id"], approve)
        self.ledger = GrantLedger(
            control_plane=self.registry, catalog=self.catalog, sink=self.sink,
            clock=lambda: self.instant,
        )
        self.calculator = CovenantCalculator(config["financials"])
        self.writeback_calls = 0
        callables = CallableRegistry()
        callables.register(self.entries["calculator"].binding.callable_ref, self.calculator)
        callables.register(self.entries["writeback"].binding.callable_ref, self.writeback_sentinel)
        self.agent = AgentFactory(control_plane=self.registry, callable_registry=callables).construct(
            definition_key=config["keys"]["agent"], definition_version=definition_version,
            bound_skills=self.ledger.bound_view(self.definition_hash),
        )

    def bootstrap(self, key: str):
        """Record the deployment's boot decision, then mint its exact-key authority."""
        event = self.audit.append(
            action="composition", key=key, version="1.0.0", resolved=True,
            occurred_at=self.instant, actor=COMPOSITION_PRINCIPAL,
        )
        return mint_at_composition(
            CompositionRegister, tenant=self.tenant, principal=COMPOSITION_PRINCIPAL,
            resource=key, decision_id=content_hash(event),
        )

    def authority(self, kind, resource: str, *, identity: str = "operator"):
        credential = self.identities[identity]
        if self.tenant not in credential.tenants:
            raise PermissionError("Credential does not include the demonstration tenant")
        decision = self.authorizer.authorize(
            grant=credential, tenant=self.tenant, action_id=kind.action_id, resource=resource,
        )
        if not decision.allowed:
            raise PermissionError(f"{credential.client_id} may not perform {kind.action_id}")
        return mint(kind, decision=decision, principal=credential.client_id, decision_id=decision.decision_id)

    def request(self, label: str, *, identity: str = "operator"):
        authority = self.authority(SkillGrantAuthority, self.config["keys"]["agent"], identity=identity)
        return self.ledger.request(authority, self.grants[label], definition=self.definition)

    def revoke(self, grant_hash: str) -> None:
        self.ledger.revoke(self.authority(SkillRevoke, grant_hash))

    def writeback_sentinel(self, arguments):
        self.writeback_calls += 1
        raise RuntimeError("The writeback sentinel must never be dispatched")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def demonstrate() -> tuple[list[str], dict]:
    demo = Demo()
    name = demo.entries["calculator"].name
    ids = list(demo.config["financials"]["counterparties"])
    arguments = {"counterparty_id": ids[0]}
    initial_hash = demo.ledger.grant_set_hash(demo.definition_hash)
    lines = ["CCF bank-agent skills demonstration (synthetic data; scripted approval)"]
    try:
        demo.agent.invoke_skill(name, arguments=arguments)
    except SkillNotBound:
        lines.append("1. Registered but ungranted skill: REFUSED (SkillNotBound)")
    else:
        raise RuntimeError("Ungranted skill unexpectedly executed")
    try:
        demo.request("calculator", identity="analyst")
    except PermissionError:
        lines.append("2. Analyst attempts to grant a skill: DENIED (authorization)")
    else:
        raise RuntimeError("Unauthorized grant unexpectedly accepted")
    grant_hash = demo.request("calculator")
    require(isinstance(grant_hash, str), f"Calculator grant refused: {grant_hash}")
    require(demo.ledger.state(grant_hash) == "effective", "Grant did not become effective")
    lines.append("3. Operator grant within policy, scripted approval: EFFECTIVE")
    surface = render_tool_surface(demo.agent.invoke_skill(name))
    active_hash = demo.ledger.grant_set_hash(demo.definition_hash)
    conditioning = demo.agent.perspective_conditioning(
        principal_id=demo.identities["analyst"].client_id, grant_set_hash=active_hash,
    )
    results = []
    for counterparty_id in ids:
        result = demo.agent.invoke_skill(name, arguments={"counterparty_id": counterparty_id})
        values = dict(result.output)
        results.append(values)
        lines.append(
            f"   {counterparty_id}: leverage {values['leverage']}x, "
            f"coverage {values['interest_coverage']}x -> {values['status']}"
        )
    calls = demo.calculator.calls
    try:
        demo.agent.invoke_skill(name, arguments={"counterparty_id": 123})
    except ArgumentRefused as exc:
        require(demo.calculator.calls == calls, "Malformed arguments reached the calculator")
        lines.append(f"4. Non-string counterparty identifier: REFUSED ({type(exc).__name__})")
    else:
        raise RuntimeError("Malformed arguments unexpectedly accepted")
    approvals_before = len(demo.sink.requests)
    refusal = demo.request("writeback")
    require(isinstance(refusal, RequirementsExceedRegime), f"Unexpected writeback result: {refusal}")
    require(len(demo.sink.requests) == approvals_before, "Writeback reached approval")
    try:
        demo.agent.invoke_skill(demo.entries["writeback"].name, arguments=arguments)
    except SkillNotBound:
        lines.append("5. Writeback grant: REFUSED (RequirementsExceedRegime); invocation: REFUSED")
    else:
        raise RuntimeError("Writeback unexpectedly bound")
    require(demo.writeback_calls == 0, "Writeback was dispatched")
    demo.revoke(grant_hash)
    try:
        demo.agent.invoke_skill(name, arguments=arguments)
    except SkillNotBound:
        lines.append("6. Calculator after revocation: REFUSED (SkillNotBound)")
    else:
        raise RuntimeError("Revoked skill unexpectedly executed")
    final_hash = demo.ledger.grant_set_hash(demo.definition_hash)
    require(final_hash == initial_hash != active_hash, "Grant-set identity did not track lifecycle")
    require(demo.agent.identity.definition_hash == demo.definition_hash, "Agent identity changed")
    lines.append("7. Agent definition unchanged; grant-set hash returned to its initial value")
    lines.append("PASS: calculation, authorization, argument validation, policy refusal and revocation")
    evidence = {
        "kind": "demonstration-evidence-not-a-DecisionReplayRecord",
        "example_tested_sdk_commit": SDK_BASELINE,
        "scenario_hash": content_hash(demo.config),
        "agent_definition_hash": demo.definition_hash,
        "grant_hash": grant_hash,
        "grant_set_hashes": {"before": initial_hash, "active": active_hash, "after": final_hash},
        "tool_surface": {"description": surface.description, "input_schema": surface.input_schema},
        "perspective_conditioning": conditioning.model_dump(mode="json"),
        "calculations": results,
        "writeback_refusal": refusal.model_dump(mode="json"),
        "call_counts": {"calculator": demo.calculator.calls, "writeback": demo.writeback_calls},
        "audit_events": [event.model_dump(mode="json") for event in demo.audit.events()],
    }
    return lines, evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, help="Write demonstration evidence as JSON")
    args = parser.parse_args()
    lines, evidence = demonstrate()
    print("\n".join(lines))
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(f"Evidence written to {args.evidence}")


if __name__ == "__main__":
    main()
