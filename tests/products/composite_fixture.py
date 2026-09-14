"""The composite deployment both proofs wire — one definition, two routes.

`D-IMPL-336` **Amendment 5 §5**. `tests/products/test_composite_integration.py`
drives it with the atomic product produced **in this process**;
`tests/crossproc/test_composite_provider_independence.py` drives the SAME
build with the product produced in **another process, over MCP**.

**Sharing this module is the proof, not a convenience.** Dave's requirement is
that acquisition rebinds *"without changing the composite's requirements or
roll-up logic"*. If each test built its own composite, "unchanged" would be a
claim about two files agreeing. Here both call :func:`build_composite`, and the
only argument that differs is the granted skill's binding.
"""

from __future__ import annotations

import copy
import pathlib
from collections.abc import Iterator, Mapping
from datetime import datetime
from typing import Any

from ccf.agents.definitions import AgentDefinition
from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot
from ccf.products.child_resolver import GrantBoundChildResolver
from ccf.products.composite import CompositeAdmissionGate
from ccf.products.door import WireRequest, door_answer
from ccf.products.request import ProductRequest
from ccf.products.resolver import GovernedResolver
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import (
    LocalCallableBinding,
    McpBinding,
    SkillArgumentSchema,
    SkillCatalog,
    SkillCatalogEntry,
    SkillRequirements,
)
from ccf.skills.dispatch import McpSkillRegistry
from ccf.skills.grants import GrantLedger, SkillGrant

from tests.deployment.conftest import (
    ARTIFACT_SET,
    PRODUCT_CLASS_KEY,
    SIGNAL_BATCH_KEY,
    SIMILARITY_KEY,
    TENANT,
    manifest_document,
    write_artifact,
)
#: The remote provider's logical server name, imported rather than restated so
#: the skill binding and the child server cannot come to name two things.
from tests.crossproc.servers.mcp_atomic_product_child import SERVER_NAME
from tests.products.provider_boot import (
    CHILD_CLASS,
    CHILD_CLASS_KEY,
    CHILD_REQUEST_CONTRACT_KEY,
    child_product_class,
    child_request_contract,
)
from tests.products.test_resolver_seam import (
    ADMITTED_AT,
    ASKED_AT,
    DEBT_PROFILE_KEY,
    OBLIGATION_ON_OK,
    PERSPECTIVE,
    PRODUCT_CLASS,
    PRODUCT_VERSION,
    REQUEST_CONTRACT_CLASS_ID,
    REQUEST_CONTRACT_DOCUMENT,
    REQUEST_CONTRACT_KEY,
    THRESHOLD_PARAMETER,
    _Booted,
    _arguments,
)

CHILD_SKILL = "child-door-skill"
CHILD_CALLABLE = "fixture.child-door"
REGIME_KEY = f"{TENANT}/policy-bundle/composite-integration"

#: The child class. A DIFFERENT class from the parent, which is the whole
#: point: a composite whose child answers the same question with the same
#: operators would demonstrate nothing about composition.
CHILD_CLASS = "fixture.child-product"
CHILD_CLASS_KEY = "fixture/product-class-child"
CHILD_SKILL = "child-door-skill"
CHILD_CALLABLE = "fixture.child-door"
CHILD_MAX_TTL_KEY = "fixture/max-ttl"

#: The regime and the agent the grant hangs off. Test-side values, every one.
REGIME_KEY = f"{TENANT}/policy-bundle/composite-integration"

#: The child's OWN request contract. The shared fixture contract pins
#: `schema_name: fixture.manifest-product`, so a child request validated
#: against it is a `product-request-violation` — which is what the first run
#: of this module measured, and correctly: a request contract is per class.
CHILD_REQUEST_CONTRACT_KEY = "fixture/request-contract-child"
CHILD_REQUEST_CONTRACT_DOCUMENT: dict[str, Any] = {
    "semver": "1.0.0",
    "class_id": "fixture.request-contract",
    "declaration": {
        "schema_name": CHILD_CLASS,
        "schema_version": "1.0.0",
        "arguments": {
            "properties": {
                "revenue_threshold": {
                    "type": "number",
                    "description": "Fixture parameter; no default anywhere.",
                }
            },
            "required": ["revenue_threshold"],
        },
    },
}


# --- the child: its own class, its own resolver, behind a real door ----------


def _parent_requires() -> list[dict[str, Any]]:
    """The parent's declared requirement: the child class, REQUIRED.

    Required rather than optional on purpose. An optional requirement has a
    declared absence treatment, so a composition that never reached the child
    at all would still serve and the test would pass for the wrong reason.
    """
    return [
        {
            "product_class": CHILD_CLASS,
            "required": True,
            "compatible_from": "1.0.0",
        }
    ]


def boot_composite(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """One deployment declaring TWO product classes: a parent and its child.

    Built from `tests/deployment`'s artifact set rather than a second fixture
    deployment, so the parent here is the same class the seam tests drive and
    the only new things are the child's class and the parent's `requires`.
    """
    root = tmp_path / "deployment"
    root.mkdir()
    for key, filename, _cid, _role, _reg, document in ARTIFACT_SET:
        if key == PRODUCT_CLASS_KEY:
            document = copy.deepcopy(document)
            document["requires"] = _parent_requires()
        write_artifact(root, filename, document)
    write_artifact(root, "product-class-child.yaml", child_product_class())
    write_artifact(root, "product-class-higher.yaml", higher_product_class())
    write_artifact(root, "request-contract-higher.yaml", higher_request_contract())
    write_artifact(root, "request-contract.yaml", REQUEST_CONTRACT_DOCUMENT)
    write_artifact(root, "request-contract-child.yaml", child_request_contract())
    write_artifact(
        root,
        "debt-profile.yaml",
        {
            "semver": "1.0.0",
            "risk_sensitivity": "1",
            "forced_llm_threshold": "0.30",
            "fail_closed_threshold": "0.70",
            "signal_obligations": [{"signal": "ok", "obligation_ref": OBLIGATION_ON_OK}],
        },
    )
    body = manifest_document()
    body["artifacts"] = [
        *body["artifacts"],
        {
            "path": "product-class-child.yaml",
            "key": CHILD_CLASS_KEY,
            "class_id": "ccf.product-class",
            "role": "register",
            "registration": "typed",
        },
        {
            "path": "product-class-higher.yaml",
            "key": HIGHER_CLASS_KEY,
            "class_id": "ccf.product-class",
            "role": "register",
            "registration": "typed",
        },
        {
            "path": "request-contract-higher.yaml",
            "key": HIGHER_REQUEST_CONTRACT_KEY,
            "class_id": REQUEST_CONTRACT_CLASS_ID,
            "role": "load",
            "registration": "typed",
        },
        {
            "path": "request-contract.yaml",
            "key": REQUEST_CONTRACT_KEY,
            "class_id": REQUEST_CONTRACT_CLASS_ID,
            "role": "load",
            "registration": "typed",
        },
        {
            "path": "request-contract-child.yaml",
            "key": CHILD_REQUEST_CONTRACT_KEY,
            "class_id": REQUEST_CONTRACT_CLASS_ID,
            "role": "load",
            "registration": "typed",
        },
        {
            "path": "debt-profile.yaml",
            "key": DEBT_PROFILE_KEY,
            "class_id": "ccf.debt-profile",
            "role": "register",
            "registration": "typed",
        },
    ]
    manifest = write_artifact(root, "manifest.yaml", body)
    control_plane = ControlPlaneRegistry()
    fabric = load_and_boot(
        manifest,
        registry=control_plane,
        connection={"database_path": str(tmp_path / "composite.sqlite3")},
    )
    for envelope in fabric.artifacts[SIGNAL_BATCH_KEY].envelopes:
        fabric.handle.worker.ingest(envelope)
    try:
        yield _Booted(
            fabric=fabric,
            control_plane=control_plane,
            store=FileArtifactStore(root=tmp_path / "artifacts"),
            root=root,
        )
    finally:
        fabric.handle.close()


def _child_resolver(booted: _Booted) -> GovernedResolver:
    """A real `GovernedResolver` for the CHILD class.

    Same wiring the parent gets, differing in the three things that make it a
    different product: its class key, the operator parameters its class
    requires, and `composite_children=None` — the child is a leaf.
    """
    arguments = _arguments(booted)
    arguments.update(
        product_class_key=CHILD_CLASS_KEY,
        request_contract_key=CHILD_REQUEST_CONTRACT_KEY,
        # The child's own operator. The parent's wiring names the traversal;
        # this names the similarity, which is what makes the composed lineage
        # a union rather than a repetition.
        operator_parameter_keys=(SIMILARITY_KEY,),
        composite_children=None,
    )
    return GovernedResolver(**arguments)


def _child_door(booted: _Booted) -> Any:
    """The `local_callable` a grant dispatches: a real door over the child.

    **This is the delivery boundary Dave's constraint names.** The child does
    not hand its contract to the composition as a Python object — it emits
    `door_answer` bytes, exactly as the MCP product tool does, and the
    composite decodes them. So the seam this test crosses is the same one a
    peered child would cross, and `content_address` is the door's own hash of
    the vessel rather than a value the test computed.
    """
    resolver = _child_resolver(booted)

    def answer(arguments: Mapping[str, str]) -> Mapping[str, str]:
        request = ProductRequest(
            schema_name=CHILD_CLASS,
            schema_version="1.0.0",
            subject=arguments["subject"],
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=datetime.fromisoformat(arguments["asked_at"]),
            parameters={THRESHOLD_PARAMETER: int(arguments["threshold"])},
        )
        resolved = resolver(
            tenant=TENANT,
            product_class=CHILD_CLASS,
            version="1.0.0",
            perspective=PERSPECTIVE,
            request=request,
        )
        return {
            "outcome": door_answer(
                resolved,
                echo=WireRequest(
                    product_id=CHILD_CLASS,
                    parameters={"subject": arguments["subject"]},
                    temporal_boundary=request.asked_at,
                ),
                resolved_request=request,
            ).decode()
        }

    return answer


def _ledger(
    booted: _Booted, *, binding: str = "local_callable", resource: str | None = None
) -> tuple[GrantLedger, str, AgentDefinition, SkillCatalog]:
    """A real grant ledger over the deployment's OWN Control Plane."""
    registry = booted.control_plane
    regime_class = declared_artifact_class("policy-bundle")
    registry.register_typed(
        REGIME_KEY,
        parse_artifact(
            {
                "class_id": "policy-bundle",
                "semver": "1.0.0",
                "declaration": {
                    "regime": "composite-integration",
                    "skill_governance": {
                        "grant_requires_approval": False,
                        "permitted_scopes": [],
                    },
                },
            },
            regime_class,
        ),
        regime_class,
    )
    definition = AgentDefinition(
        schema_version="1.0.0",
        artifact_version="1.0.0",
        name="composite-assembler",
        tenant=TENANT,
        archetypes=("context_assembly",),
        context_contract={
            "consumes": [{"product_class": CHILD_CLASS, "schema_version": "1.0.0"}]
        },
        perspective={"role": PERSPECTIVE.role, "selection_params": {}},
        policy_regime={"ref": f"ccf-artifact://{REGIME_KEY}@1.0.0"},
        halflife_debt_profile={"ref": f"ccf-artifact://{TENANT}/debt-profile/x@1.0.0"},
        instruction_bindings=(),
    )
    catalog = SkillCatalog(registry)
    catalog.register(
        SkillCatalogEntry(
            schema_version="1.0.0",
            artifact_version="1.0.0",
            name=CHILD_SKILL,
            tenant=TENANT,
            skill_type=binding,
            description="answers the child product class through its door",
            argument_schema=SkillArgumentSchema(
                properties={
                    "subject": {
                        "type": "string",
                        "description": "The account the child answers about.",
                    },
                    "asked_at": {
                        "type": "string",
                        "description": "The composition's one reconstruction instant.",
                    },
                    "threshold": {
                        "type": "string",
                        "description": "The class-declared threshold parameter.",
                    },
                },
                required=frozenset({"subject", "asked_at", "threshold"}),
            ),
            binding=(
                McpBinding(server=SERVER_NAME, resource=resource or "")
                if binding == "mcp"
                else LocalCallableBinding(callable_ref=CHILD_CALLABLE)
            ),
            requirements=SkillRequirements(
                required_scopes=frozenset(), required_context_products=frozenset()
            ),
            produces=CHILD_CLASS,
        )
    )
    ledger = GrantLedger(
        control_plane=registry,
        catalog=catalog,
        sink=None,
        clock=lambda: ADMITTED_AT,
    )
    return ledger, content_hash(definition), definition, catalog


def build_composite(
    booted: _Booted,
    *,
    grant: bool = True,
    binding: str = "local_callable",
    mcp_skills: McpSkillRegistry | None = None,
    resource: str | None = None,
) -> tuple[GovernedResolver, GrantBoundChildResolver]:
    """The composite, wired. **Only ``binding`` changes between the two proofs.**

    Args:
        booted: The consuming deployment.
        grant: Whether the producing skill is actually made effective. ``False``
            is the negative control — the catalog entry, the callable and the
            door all still exist.
        binding: ``"local_callable"`` produces the atomic product in this
            process; ``"mcp"`` reads it from a provider that produced it
            elsewhere. **Nothing else in this function reads it**, which is the
            point: the composite's `requires`, its gate, its roll-up and its
            resolver arguments are identical either way.
        mcp_skills: Required for the ``mcp`` binding — the deployment's MCP
            skill registry, built at its composition root.
        resource: The logical resource name the binding selects.
    """
    ledger, agent_hash, definition, catalog = _ledger(booted, binding=binding, resource=resource)
    if grant:
        outcome = ledger.request(
            SkillGrant(
                schema_version="1.0.0",
                artifact_version="1.0.0",
                name=f"grant-{CHILD_SKILL}",
                tenant=TENANT,
                agent_definition_hash=agent_hash,
                skill_name=CHILD_SKILL,
                skill_version="1.0.0",
            ),
            definition=definition,
            actor="composite-operator",
        )
        assert isinstance(outcome, str), outcome
    callables = CallableRegistry()
    callables.register(CHILD_CALLABLE, _child_door(booted))
    arguments = _arguments(booted)
    children = GrantBoundChildResolver(
        ledger=ledger,
        agent_definition_hash=agent_hash,
        gate=CompositeAdmissionGate(
            tenant_id=TENANT,
            consumer_scope="consumer://composite-integration",
            registry=booted.control_plane,
        ),
        # The deployment states what its children are asked. The SDK holds no
        # domain value and cannot know (`D-IMPL-38`).
        child_arguments=lambda requirement, asked_at: {
            "subject": "acct-1",
            "asked_at": asked_at.isoformat(),
            "threshold": "1000",
        },
        callable_registry=callables,
        artifact_store=booted.store,
        mcp_skills=mcp_skills,
    )
    arguments.update(composite_children=children)
    return GovernedResolver(**arguments), children


def ask_composite(resolver: GovernedResolver) -> Any:
    return resolver(
        tenant=TENANT,
        product_class=PRODUCT_CLASS,
        version=PRODUCT_VERSION,
        perspective=PERSPECTIVE,
        request=ProductRequest(
            schema_name=PRODUCT_CLASS,
            schema_version=PRODUCT_VERSION,
            subject="acct-1",
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=ASKED_AT,
            parameters={THRESHOLD_PARAMETER: 1000},
        ),
    )




# --- INT-01b: the nested chain, leaf -> composite -> higher composite --------

HIGHER_CLASS = "fixture.higher-product"
HIGHER_CLASS_KEY = "fixture/product-class-higher"
HIGHER_REQUEST_CONTRACT_KEY = "fixture/request-contract-higher"
HIGHER_SKILL = "composite-door-skill"
HIGHER_CALLABLE = "fixture.composite-door"
HIGHER_REGIME_KEY = f"{TENANT}/policy-bundle/higher-composite"


def higher_product_class() -> dict[str, Any]:
    """A class whose declared child is ITSELF a composite.

    `INT-01b`. Its operator is the traversal the middle class also runs, so
    the nesting is what this fixture varies and not the operator set — the
    union across two levels is asserted from the LEAF's operator appearing at
    the top, which it can only do by travelling through the middle.
    """
    return {
        "semver": "1.0.0",
        "schema_name": HIGHER_CLASS,
        "schema_version": "1.0.0",
        "ttl_anchor": "from_decision",
        "assembly_mode": "algorithmic",
        "max_ttl_key": "fixture/max-ttl",
        "required_operator_keys": ["traversal.typed-neighborhood"],
        "requires": [
            {
                "product_class": PRODUCT_CLASS,
                "required": True,
                "compatible_from": PRODUCT_VERSION,
            }
        ],
    }


def higher_request_contract() -> dict[str, Any]:
    return {
        "semver": "1.0.0",
        "class_id": "fixture.request-contract",
        "declaration": {
            "schema_name": HIGHER_CLASS,
            "schema_version": "1.0.0",
            "arguments": {
                "properties": {
                    "revenue_threshold": {
                        "type": "number",
                        "description": "Fixture parameter; no default anywhere.",
                    }
                },
                "required": ["revenue_threshold"],
            },
        },
    }


def _composite_door(inner: GovernedResolver) -> Any:
    """A door over the MIDDLE composite, so it can be someone else's child.

    The middle product crosses the same `door_answer` boundary the leaf does.
    Nothing about being a composite changes how it is acquired — which is the
    property `INT-01b` exists to show.
    """

    def answer(arguments: Mapping[str, str]) -> Mapping[str, str]:
        request = ProductRequest(
            schema_name=PRODUCT_CLASS,
            schema_version=PRODUCT_VERSION,
            subject=arguments["subject"],
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=datetime.fromisoformat(arguments["asked_at"]),
            parameters={THRESHOLD_PARAMETER: int(arguments["threshold"])},
        )
        resolved = inner(
            tenant=TENANT,
            product_class=PRODUCT_CLASS,
            version=PRODUCT_VERSION,
            perspective=PERSPECTIVE,
            request=request,
        )
        return {
            "outcome": door_answer(
                resolved,
                echo=WireRequest(
                    product_id=PRODUCT_CLASS,
                    parameters={"subject": arguments["subject"]},
                    temporal_boundary=request.asked_at,
                ),
                resolved_request=request,
            ).decode()
        }

    return answer


def build_higher_composite(
    booted: _Booted, inner: GovernedResolver
) -> tuple[GovernedResolver, GrantBoundChildResolver]:
    """The top of the chain, acquiring the middle composite as its child."""
    registry = booted.control_plane
    regime_class = declared_artifact_class("policy-bundle")
    registry.register_typed(
        HIGHER_REGIME_KEY,
        parse_artifact(
            {
                "class_id": "policy-bundle",
                "semver": "1.0.0",
                "declaration": {
                    "regime": "higher-composite",
                    "skill_governance": {
                        "grant_requires_approval": False,
                        "permitted_scopes": [],
                    },
                },
            },
            regime_class,
        ),
        regime_class,
    )
    definition = AgentDefinition(
        schema_version="1.0.0",
        artifact_version="1.0.0",
        name="higher-composite-assembler",
        tenant=TENANT,
        archetypes=("context_assembly",),
        context_contract={
            "consumes": [
                {"product_class": PRODUCT_CLASS, "schema_version": PRODUCT_VERSION}
            ]
        },
        perspective={"role": PERSPECTIVE.role, "selection_params": {}},
        policy_regime={"ref": f"ccf-artifact://{HIGHER_REGIME_KEY}@1.0.0"},
        halflife_debt_profile={"ref": f"ccf-artifact://{TENANT}/debt-profile/x@1.0.0"},
        instruction_bindings=(),
    )
    catalog = SkillCatalog(registry)
    catalog.register(
        SkillCatalogEntry(
            schema_version="1.0.0",
            artifact_version="1.0.0",
            name=HIGHER_SKILL,
            tenant=TENANT,
            skill_type="local_callable",
            description="answers the middle composite through its door",
            argument_schema=SkillArgumentSchema(
                properties={
                    "subject": {"type": "string", "description": "The account."},
                    "asked_at": {"type": "string", "description": "The instant."},
                    "threshold": {"type": "string", "description": "The threshold."},
                },
                required=frozenset({"subject", "asked_at", "threshold"}),
            ),
            binding=LocalCallableBinding(callable_ref=HIGHER_CALLABLE),
            requirements=SkillRequirements(
                required_scopes=frozenset(), required_context_products=frozenset()
            ),
            produces=PRODUCT_CLASS,
        )
    )
    ledger = GrantLedger(
        control_plane=registry, catalog=catalog, sink=None, clock=lambda: ADMITTED_AT
    )
    assert isinstance(
        ledger.request(
            SkillGrant(
                schema_version="1.0.0",
                artifact_version="1.0.0",
                name=f"grant-{HIGHER_SKILL}",
                tenant=TENANT,
                agent_definition_hash=content_hash(definition),
                skill_name=HIGHER_SKILL,
                skill_version="1.0.0",
            ),
            definition=definition,
            actor="higher-operator",
        ),
        str,
    )
    callables = CallableRegistry()
    callables.register(HIGHER_CALLABLE, _composite_door(inner))
    children = GrantBoundChildResolver(
        ledger=ledger,
        agent_definition_hash=content_hash(definition),
        gate=CompositeAdmissionGate(
            tenant_id=TENANT,
            consumer_scope="consumer://higher-composite",
            registry=registry,
        ),
        child_arguments=lambda requirement, asked_at: {
            "subject": "acct-1",
            "asked_at": asked_at.isoformat(),
            "threshold": "1000",
        },
        callable_registry=callables,
        artifact_store=booted.store,
    )
    arguments = _arguments(booted)
    arguments.update(
        product_class_key=HIGHER_CLASS_KEY,
        request_contract_key=HIGHER_REQUEST_CONTRACT_KEY,
        composite_children=children,
    )
    return GovernedResolver(**arguments), children


def ask_higher(resolver: GovernedResolver) -> Any:
    return resolver(
        tenant=TENANT,
        product_class=HIGHER_CLASS,
        version="1.0.0",
        perspective=PERSPECTIVE,
        request=ProductRequest(
            schema_name=HIGHER_CLASS,
            schema_version="1.0.0",
            subject="acct-1",
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=ASKED_AT,
            parameters={THRESHOLD_PARAMETER: 1000},
        ),
    )
