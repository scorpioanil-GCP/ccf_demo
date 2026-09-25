"""The paved-road consumer fixture: two deployments, four documents, three callables.

`D-IMPL-343`, the consumer half. Shared by the SDK-level consumer proof
(``tests/products/test_paved_consumer.py``) and the producer's door process
(``tests/crossproc/servers/paved_fixture_door.py``), so the class the producer
serves and the class the consumer requires are one constant, never two
spellings.

**The producer** is the servable single-file fixture deployment, re-labeled as
its own class under its own tenant and given the three paved sections; it is
opened with :func:`ccf.products.product.open_product` and served through
:func:`ccf_runtime.mcp.product_door.open_door` in another process.

**The consumer** is the same servable fixture — the parent class — declaring
that it REQUIRES the producer's class, plus the four declarations the derived
chain reads: ``producers:``, ``skills:``, ``agent:`` and the policy regime's
``skill_governance``. Every value the consumer states about the producer is a
NAME or an identity (a server name, a producer id, a tenant, two environment
variable names, a floor); no address and no credential appears in either
document.
"""

from __future__ import annotations

import copy
import pathlib
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from ccf.agents.definitions import AgentDefinition
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import DEPLOYMENT_CONFIG, DeploymentConfig, load_artifact, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry, RegistrationRefusal
from ccf.deployment.classes import resolve_artifact_class
from ccf.deployment.config import derive_deployment
from ccf.deployment.environment import load_environment_document
from ccf.deployment.manifest import manifest_under_tenant, register_manifest_entries
from ccf.graph.protocols import GraphView
from ccf.halflife.assessment import DebtFactors
from ccf.halflife.debt import DebtAssessment, assess_debt
from ccf.products.child_resolver import ChildQuestion
from ccf.products.contract import ChildRequirement
from ccf.products.product import AcquisitionContext, AssessmentContext
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.signal.envelope import SignalEnvelope
from ccf.skills.catalog import SkillCatalog, SkillCatalogEntry
from ccf.skills.grants import ApprovalSink, GrantLedger, GrantRefusal, RefusingApprovalSink, SkillGrant
from tests.deployment.conftest import write_artifact
from tests.skills.authority import grant_capability
from tests.deployment.test_replay_binding import (
    PRODUCT_CLASS as PARENT_CLASS,
    PRODUCT_VERSION as PARENT_VERSION,
    TENANT as CONSUMER_TENANT,
    THRESHOLD_PARAMETER,
    _servable_config,
)

__all__ = [
    "ASKED_AT",
    "ADMITTED_AT",
    "CHILD_CLASS",
    "CHILD_VERSION",
    "CONSUMER_TENANT",
    "PARENT_CLASS",
    "PARENT_VERSION",
    "PRODUCER_ID",
    "PRODUCER_TENANT",
    "SERVER_NAME",
    "SKILL",
    "AGENT_NAME",
    "ENDPOINT_VAR",
    "CREDENTIAL_VAR",
    "CHILD_DSN_VAR",
    "PARENT_DSN_VAR",
    "THRESHOLD_PARAMETER",
    "Acquire",
    "assess",
    "plan_factory",
    "questions",
    "consumer_config",
    "consumer_environment_text",
    "producer_config",
    "producer_environment_text",
    "write_tree",
]

#: The instant every question in the proof is asked at, and the clock the
#: consumer admits at — seven minutes on, as the SDK's own fixtures pin it.
ASKED_AT = datetime(2026, 3, 2, 12, 0, tzinfo=UTC)
ADMITTED_AT = ASKED_AT + timedelta(minutes=7)
OBSERVED_AT = datetime(2026, 3, 2, 11, 0, tzinfo=UTC)

#: The child: the producer's class, lane and tenant, and the identity its door
#: asserts. Declared here once; the consumer's documents restate the three the
#: registration holds the answer to (`D-IMPL-340`, R-6).
CHILD_CLASS = "fixture.paved-child"
CHILD_VERSION = "1.0.0"
PRODUCER_TENANT = "paved-child-tenant"
PRODUCER_ID = "paved-child-egress"

#: The consumer's names for the producer: a logical server name, the skill
#: label, the composing agent's name, and the two environment-variable NAMES
#: the endpoint and credential are read from.
SERVER_NAME = "paved-child-producer"
SKILL = "child-ask"
AGENT_NAME = "paved-consumer"
ENDPOINT_VAR = "PAVED_CHILD_URL"
CREDENTIAL_VAR = "PAVED_CHILD_TOKEN"
CHILD_DSN_VAR = "PAVED_CHILD_DSN"
PARENT_DSN_VAR = "PAVED_FIXTURE_DSN"


# --- the three callables ---------------------------------------------------------


class Acquire:
    """A spy acquisition: records what it was handed, emits one dated envelope."""

    def __init__(self, *, entity: str = "acct-1") -> None:
        self.contexts: list[AcquisitionContext] = []
        self._entity = entity

    def __call__(self, context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
        self.contexts.append(context)
        return (
            SignalEnvelope.model_validate(
                {
                    "tenant_id": context.tenant_id,
                    "envelope_id": "envelope-paved-1",
                    "source": {"system_id": "fixture-system"},
                    "ingestion_timestamp": context.instant,
                    "observed_time": OBSERVED_AT,
                    "raw_payload": {
                        "account_ref": self._entity,
                        "classification": "fixture-open",
                        "label": "fixture account",
                    },
                }
            ),
        )


class _Projection:
    """The smallest Π that still applies the caller's parameter."""

    def __init__(self, *, plan_id: str, required: tuple[str, ...], request: ProductRequest) -> None:
        self._plan_id = plan_id
        self._required = required
        self._request = request

    @property
    def plan_id(self) -> str:
        return self._plan_id

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
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "threshold": str(self._request.parameters[THRESHOLD_PARAMETER]),
                "assembled": len(list(view.entities)),
            },
        )


def plan_factory(*, required: tuple[str, ...], request: ProductRequest) -> _Projection:
    """A NAMED factory whose only operator source is the ``required`` tuple (`D-IMPL-137`)."""
    return _Projection(plan_id=request.schema_name, required=required, request=request)


def assess(context: AssessmentContext) -> DebtAssessment:
    assert context.profile is not None
    return assess_debt(
        DebtFactors(freshness=Decimal(1), completeness=Decimal(1), semantic_consistency=Decimal(1)),
        profile=context.profile,
    )


def questions(requirement: ChildRequirement, request: ProductRequest) -> ChildQuestion:
    """The consumer's ONE mapping: the parent's subject reaches the child as ITS subject."""
    return ChildQuestion(
        subject=request.subject,
        intent="fixture-intent",
        freshness="fixture-freshness",
        parameters={THRESHOLD_PARAMETER: request.parameters[THRESHOLD_PARAMETER]},
    )


# --- the documents ------------------------------------------------------------------


#: The two replay classes every paved fixture's `replay:` section declares —
#: named once so a test declaring a store of its own names the same classes.
RECORD_CLASS = "ccf.replay-record"
QUERY_PIN_CLASS = "ccf.graph-query"


def _paved_sections(*, producer_id: str, tenant: str) -> dict[str, Any]:
    return {
        "replay": {
            "record_class": RECORD_CLASS,
            "query_pin_class": QUERY_PIN_CLASS,
            "store_dirname": "artifact-store",
        },
        "ttl": {"max_ttl_seconds": 3600, "product_ttl_seconds": 600},
        "door": {
            "producer_id": producer_id,
            "producer_tenant": tenant,
            "tool_description": "asks this fixture product a question",
            "required_scope": "ccf:egress",
        },
    }


def producer_config(**overrides: Any) -> dict[str, Any]:
    """The producer: the servable fixture, re-labeled as the child class under its own tenant."""
    document = _servable_config(**_paved_sections(producer_id=PRODUCER_ID, tenant=PRODUCER_TENANT))
    document["tenant_id"] = PRODUCER_TENANT
    document["product_class"]["schema_name"] = CHILD_CLASS
    document["product_class"]["schema_version"] = CHILD_VERSION
    document["request_contract"]["schema_name"] = CHILD_CLASS
    document["request_contract"]["schema_version"] = CHILD_VERSION
    document.update(overrides)
    return document


def producer_environment_text() -> str:
    return "\n".join(
        [
            "config: ccf_config.yaml",
            "substrate: {setting: database_path, prefix: paved_child, suffix: .sqlite3}",
            "sources:",
            "  store:",
            f"    dsn: {{from_env: {CHILD_DSN_VAR}, remedy: 'export {CHILD_DSN_VAR} with the fixture DSN'}}",
            "door:",
            f"  credential: {{from_env: {CREDENTIAL_VAR}, remedy: 'set, or leave unset to mint one per boot'}}",
            "  issuer_url: {from_env: PAVED_CHILD_ISSUER, remedy: 'export the issuer (stdio only)'}",
            "  resource_server_url: {from_env: PAVED_CHILD_RESOURCE, remedy: 'export the resource server (stdio only)'}",
            "",
        ]
    )


def producer_section(
    *,
    producer_id: str = PRODUCER_ID,
    producer_tenant: str = PRODUCER_TENANT,
    offered_class: str = CHILD_CLASS,
    versions_from: str = CHILD_VERSION,
) -> dict[str, Any]:
    """One `producers.*` body — names only, never an address (`D-IMPL-340`)."""
    return {
        "server": SERVER_NAME,
        "producer_id": producer_id,
        "producer_tenant": producer_tenant,
        "endpoint_from_env": ENDPOINT_VAR,
        "credential_from_env": CREDENTIAL_VAR,
        "offers": [{"product_class": offered_class, "versions_from": versions_from}],
    }


def skill_section(**overrides: Any) -> dict[str, Any]:
    """One `skills.*` body: the author's two lanes, description, requirements and `produces`."""
    body: dict[str, Any] = {
        "schema_version": "1.0.0",
        "artifact_version": "1.0.0",
        "description": "asks the registered paved-child producer a governed question",
        "produces": CHILD_CLASS,
        "requirements": {"required_scopes": [], "required_context_products": []},
    }
    body.update(overrides)
    return body


def agent_section(**overrides: Any) -> dict[str, Any]:
    """The composing agent: its name, its two lanes and its archetype — the rest is derived."""
    body: dict[str, Any] = {
        "schema_version": "1.0.0",
        "artifact_version": "1.0.0",
        "name": AGENT_NAME,
        "archetypes": ["context_assembly"],
    }
    body.update(overrides)
    return body


def consumer_config(
    *,
    compatible_from: str = CHILD_VERSION,
    producers: Mapping[str, Mapping[str, Any]] | None | str = "declared",
    skills: Mapping[str, Mapping[str, Any]] | None | str = "declared",
    agent: Mapping[str, Any] | None | str = "declared",
    governance: Mapping[str, Any] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    """The consumer: the parent fixture requiring the child, with its four declarations.

    ``producers``, ``skills`` and ``agent`` take the sentinel ``"declared"``
    for the canonical section, ``None`` to omit the section, or a body.
    """
    document = _servable_config(**_paved_sections(producer_id="paved-consumer-egress", tenant=CONSUMER_TENANT))
    del document["door"]  # the consumer opens no door in this proof
    document["product_class"]["requires"] = [
        {"product_class": CHILD_CLASS, "required": True, "compatible_from": compatible_from}
    ]
    # The regime's skilling envelope, and the two `key:` overrides an agent's
    # pinned references need (`ccf-artifact://{tenant}/{class}/{name}@{version}`).
    document["policy"]["key"] = f"{CONSUMER_TENANT}/policy-bundle/paved-consumer"
    document["policy"]["skill_governance"] = dict(
        governance or {"grant_requires_approval": False, "permitted_scopes": []}
    )
    document["debt_profile"]["key"] = f"{CONSUMER_TENANT}/ccf.debt-profile/paved-consumer"
    if producers == "declared":
        document["producers"] = {"child": producer_section()}
    elif producers is not None:
        document["producers"] = copy.deepcopy(dict(producers))
    if skills == "declared":
        document["skills"] = {SKILL: skill_section()}
    elif skills is not None:
        document["skills"] = copy.deepcopy(dict(skills))
    if agent == "declared":
        document["agent"] = agent_section()
    elif agent is not None:
        document["agent"] = copy.deepcopy(dict(agent))
    document.update(overrides)
    return document


def consumer_environment_text(*, remote: bool = True) -> str:
    lines = [
        "config: ccf_config.yaml",
        "substrate: {setting: database_path, prefix: paved_consumer, suffix: .sqlite3}",
        "sources:",
        "  store:",
        f"    dsn: {{from_env: {PARENT_DSN_VAR}, remedy: 'export {PARENT_DSN_VAR} with the fixture DSN'}}",
    ]
    if remote:
        lines += ["remote: {call_timeout_seconds: 60}"]
    return "\n".join(lines) + "\n"


def write_tree(root: pathlib.Path, *, config: Mapping[str, Any], environment: str) -> pathlib.Path:
    """Write the two documents under ``root`` and return it."""
    root.mkdir(parents=True, exist_ok=True)
    write_artifact(root, "ccf_config.yaml", config)
    (root / "ccf_environment.yaml").write_text(environment, encoding="utf-8")
    return root


# --- the grants a paved deployment opens over -------------------------------------------------

#: The principal that grants a deployment's declared skills to its agent through the
#: ledger — an authorized operator, never the road and never the agent itself.
GRANTING_PRINCIPAL = "an-authorized-operator"


def grants_in_force(
    root: pathlib.Path,
    *,
    principal: str = GRANTING_PRINCIPAL,
    sink: ApprovalSink | None = None,
    control_plane: ControlPlaneRegistry | None = None,
    clock: Any = lambda: ADMITTED_AT,
) -> tuple[ControlPlaneRegistry, tuple[str | GrantRefusal | RegistrationRefusal, ...]]:
    """Grant the deployment at ``root`` its declared skills, the way an operator would.

    :func:`~ccf.products.product.open_product` requests no grant (D-IMPL-353
    §1.6; D-IMPL-354): a grant is a ``skill.grant`` door action requiring
    ``Authorized[SkillGrant]``, which a composition root cannot mint, so a
    deployment declaring ``skills:`` is opened over a Control Plane on which an
    authorized principal already granted them — the migration `353-07` names.
    This does exactly that, on the deployment's own derived documents: the
    regime, the agent and the catalog entries are registered as the road
    registers them (composition-time ``Register``, keys placed under the
    tenant), then ONE grant per declared skill is requested through the ledger
    under a capability minted for ``principal``. Returns the plane and every
    grant outcome, so a test about a refused grant reads the ledger's reason.
    """
    environment = load_environment_document(root)
    config = load_artifact((root / environment.config).read_text(encoding="utf-8"), DEPLOYMENT_CONFIG)
    assert isinstance(config, DeploymentConfig) and config.tenant_id is not None
    derived = derive_deployment(config)
    registry = control_plane if control_plane is not None else ControlPlaneRegistry()
    declared_keys = derived.keys
    if declared_keys.agent is None or not declared_keys.skills:
        return registry, ()
    declared_wanted = frozenset({declared_keys.policy_bundle, declared_keys.agent, *declared_keys.skills})
    declared = {
        entry.key: parse_artifact(derived.documents[entry.key], resolve_artifact_class(entry.class_id))
        for entry in derived.manifest.artifacts
        if entry.key in declared_wanted
    }
    manifest, parsed, keys = manifest_under_tenant(derived.manifest, declared, declared_keys, tenant=config.tenant_id)
    assert keys is not None and keys.agent is not None
    register_manifest_entries(manifest, parsed, registry=registry, tenant=config.tenant_id, only=frozenset({keys.policy_bundle, keys.agent, *keys.skills}))
    agent = parsed[keys.agent]
    assert isinstance(agent, AgentDefinition)
    ledger = GrantLedger(
        control_plane=registry,
        catalog=SkillCatalog(registry),
        sink=sink if sink is not None else RefusingApprovalSink(),
        clock=clock,
    )
    outcomes: list[str | GrantRefusal | RegistrationRefusal] = []
    for key in keys.skills:
        entry = parsed[key]
        assert isinstance(entry, SkillCatalogEntry)
        outcomes.append(
            ledger.request(
                grant_capability(agent, principal=principal),
                SkillGrant(
                    schema_version=entry.schema_version, artifact_version=entry.artifact_version,
                    name=entry.name, tenant=entry.tenant, agent_definition_hash=content_hash(agent),
                    skill_name=entry.name, skill_version=entry.artifact_version,
                ),
                definition=agent,
            )
        )
    return registry, tuple(outcomes)


def granted_control_plane(root: pathlib.Path, **arguments: Any) -> ControlPlaneRegistry:
    """The Control Plane a paved deployment opens over, every declared grant in force."""
    registry, outcomes = grants_in_force(root, **arguments)
    refused = [outcome for outcome in outcomes if not isinstance(outcome, str)]
    assert not refused, refused
    return registry
