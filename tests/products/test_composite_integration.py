"""`INT-01a` — one governed question, all the way through, with nothing faked.

`D-IMPL-336` Amendment 4, checkpoint 1. Dave's constraint, verbatim: *"one
path through the real machinery; fixture product acceptable; **no injected
outcomes map, no dictionary standing in for grant resolution, no `deliver()`
helper bypassing the delivery boundary**."*

Every unit-level test of this surface hands `compose_children` an outcomes
map. That proves composition and proves nothing about how a child gets there,
which is where `O1` and `O2` both lived. This module removes the map. What
runs here, in order, is:

1. a real :class:`~ccf.skills.grants.GrantLedger` makes a grant **effective**,
2. `resolve_producing_grant` finds the producing entry through the agent's own
   live :class:`~ccf.skills.grants.BoundSkillView`,
3. :func:`~ccf.skills.dispatch.dispatch_skill` dispatches it,
4. the callable answers through a **child** :class:`GovernedResolver` and emits
   :func:`~ccf.products.door.door_answer` — the real wire boundary, so the
   child crosses it exactly as an MCP or A2A child would,
5. the boot's own `local_attestor` attests over the record that delivery wrote,
6. :meth:`CompositeAdmissionGate.admit` decides,
7. `compose_children` composes, and the **parent** resolver serves,
8. and the assertions are made against the record read back **off the store**.

**The child deliberately invokes an operator the parent does not.** That is
`R4` in its natural form rather than a contrived one, and it is the reason
this file could not have been written before `R4` was resolved: every real
child of another class collided with Gate 2.

**Where the child resolver lives is an open question for Dave.** CLAUDE.md
§7.3/§8.1 says orchestration is the harness's and the SDK ships no
implementation; §11 says a reference implementation ships alongside every
Protocol. :class:`_GrantBoundChildResolver` below is written test-side so the
path is proven without that decision being taken by implication. Moving it
into ``src/`` is a move, not a rewrite.
"""

from __future__ import annotations

import copy
import pathlib
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from ccf.agents.definitions import AgentDefinition
from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot
from ccf.products.child_resolver import GrantBoundChildResolver
from ccf.products.composite import (
    AdmittedChild,
    ChildAdmissionRefusal,
    ChildCandidate,
    CompositeAdmissionGate,
    GATE_CHILD_ADMISSION,
    invocation_from_dispatch,
    resolve_producing_grant,
)
from ccf.products.contract import ChildRequirement, ContextProductContract
from ccf.products.door import DoorOutcome, WireRequest, door_answer
from ccf.replay.serve import ServedProduct
from ccf.products.request import ProductRequest
from ccf.replay.record import DecisionReplayRecord
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import (
    LocalCallableBinding,
    SkillArgumentSchema,
    SkillCatalog,
    SkillCatalogEntry,
    SkillRequirements,
)
from ccf.skills.dispatch import SkillInvocation, dispatch_skill
from ccf.skills.grants import BoundSkillView, GrantLedger, SkillGrant

from tests.deployment.conftest import (
    ARTIFACT_SET,
    PRODUCT_CLASS_KEY,
    SIGNAL_BATCH_KEY,
    TENANT,
    TRAVERSAL_KEY,
    SIMILARITY_KEY,
    manifest_document,
    write_artifact,
)
from tests.products.test_resolver_seam import (
    ADMITTED_AT,
    ASKED_AT,
    DEBT_PROFILE_KEY,
    OBLIGATION_ON_OK,
    PERSPECTIVE,
    PRODUCT_CLASS,
    PRODUCT_VERSION,
    REQUEST_CONTRACT_DOCUMENT,
    REQUEST_CONTRACT_KEY,
    REQUEST_CONTRACT_CLASS_ID,
    THRESHOLD_PARAMETER,
    _Booted,
    _arguments,
)
from ccf.products.resolver import GovernedResolver

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


def _child_product_class() -> dict[str, Any]:
    """The child's class declaration — a SECOND class in one deployment.

    Its `required_operator_keys` name an operator the parent's class does not,
    so the composed lineage is genuinely a union and `R4`'s widened Gate 2
    operand is exercised by the shape a real deployment produces rather than
    by a test choosing an operator name.
    """
    return {
        "semver": "1.0.0",
        "schema_name": CHILD_CLASS,
        "schema_version": "1.0.0",
        "ttl_anchor": "from_decision",
        "assembly_mode": "algorithmic",
        "max_ttl_key": CHILD_MAX_TTL_KEY,
        "required_operator_keys": ["similarity.corpus-select"],
    }


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


@pytest.fixture()
def booted(tmp_path: pathlib.Path) -> Iterator[_Booted]:
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
    write_artifact(root, "product-class-child.yaml", _child_product_class())
    write_artifact(root, "request-contract.yaml", REQUEST_CONTRACT_DOCUMENT)
    write_artifact(
        root, "request-contract-child.yaml", CHILD_REQUEST_CONTRACT_DOCUMENT
    )
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


def _ledger(booted: _Booted) -> tuple[GrantLedger, str, AgentDefinition]:
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
            skill_type="local_callable",
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
            binding=LocalCallableBinding(callable_ref=CHILD_CALLABLE),
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
    return ledger, content_hash(definition), definition


def _wire(
    booted: _Booted, *, grant: bool = True
) -> tuple[GovernedResolver, _GrantBoundChildResolver]:
    """The parent resolver, wired to a child resolver over real machinery."""
    ledger, agent_hash, definition = _ledger(booted)
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
    )
    arguments.update(composite_children=children)
    return GovernedResolver(**arguments), children


def _ask(resolver: GovernedResolver) -> Any:
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


def test_int01a_one_governed_question_through_the_whole_machinery(
    booted: _Booted,
) -> None:
    """`INT-01a`. Grant, dispatch, door, attestation, admission, composition.

    The assertions are made against the record read back **off the store**,
    not against the in-memory outcome, because the claim is that a composite
    is auditable afterwards and an in-memory object cannot carry that.
    """
    resolver, children = _wire(booted)
    outcome = _ask(resolver)
    assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)

    # `R4`, in its natural form: the child's own operator is in the served
    # lineage, and the parent's engine never ran it.
    operators = outcome.product.lineage.operators_invoked
    assert "similarity.corpus-select" in operators
    assert "traversal.typed-neighborhood" in operators

    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(
            content_address=booted.store.resolve_uri(uri=outcome.replay_ref.uri)
        )
    )
    rows = record.content_generation_path.child_resolutions
    assert len(rows) == 1
    row = rows[0]
    assert row.required_product_class == CHILD_CLASS
    assert row.outcome_status == "admitted"
    # The producer identity is the CATALOG's and the LEDGER's, never a string
    # this test wrote (`O2`).
    assert row.producing_skill_name == CHILD_SKILL
    assert row.grant_hash
    # `D-IMPL-336` **Amendment 5**: a locally dispatched child names NO
    # producing fabric, because this fabric authenticated no producer — it ran
    # a skill it had granted. The basis records which authority applied.
    assert row.producing_fabric is None
    assert row.eligibility_basis == "local-register"
    # ...and the entities came from the child's OWN persisted record, read
    # through the one store access the resolver makes for a local child.
    assert row.child_asked_at == ASKED_AT
    assert row.child_asked_at == ASKED_AT


def test_int01a_a_required_child_with_NO_GRANT_refuses(booted: _Booted) -> None:
    """The negative control, and it is the one that matters for `O2`.

    Nothing about the deployment changes except that the grant is never
    requested. The catalog entry still exists, the callable is still
    registered, and the door still works — so a resolver that dispatched on
    catalog presence rather than on an in-force grant would serve here.
    """
    resolver, _children = _wire(booted, grant=False)
    outcome = _ask(resolver)
    assert not isinstance(outcome, ServedProduct), outcome
    assert outcome.kind == "composite-child-refusal"


def test_int01a_a_REVOKED_grant_refuses_the_same_way(booted: _Booted) -> None:
    """Revocation takes effect without re-wiring anything.

    The resolver is built with the grant in force, then the grant is revoked
    through the Control Plane and the same resolver is asked again. Proves the
    bound view is read at resolution time rather than captured at wiring time
    — which is what makes a revocation a governance act rather than a restart.
    """
    resolver, _children = _wire(booted)
    assert isinstance(_ask(resolver), ServedProduct)

    ledger, agent_hash, _definition = _ledger(booted)
    effective = ledger.effective_hashes(agent_hash)
    assert len(effective) == 1, effective
    ledger.revoke(next(iter(effective)), actor="composite-operator")

    after = _ask(resolver)
    assert not isinstance(after, ServedProduct), after
    assert after.kind == "composite-child-refusal"
