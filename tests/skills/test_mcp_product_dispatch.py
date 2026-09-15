"""`D-IMPL-340` — the `mcp_product` dispatch surface, below the composite.

What the dispatch layer alone promises: the tool it asks is the door's own
(the two constants are one name); an `mcp_product` entry is dispatched with a
`ProductQuestion` or not at all; the question's identity binds every axis;
every argument the producer receives has one source; a registered producer
that cannot answer is a minted `McpProductFailure` value with a recordable
detail; the registry refuses one logical name for two registrations.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.controlplane.audit import AuditLog
from ccf.mcp.errors import McpServerUnreachable, McpTimeout, McpToolFailed
from ccf.products.door import PRODUCT_REQUEST_TOOL as DOOR_TOOL
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import (
    McpProductBinding,
    SkillArgumentSchema,
    SkillCatalogEntry,
    SkillRequirements,
)
from ccf.skills.dispatch import (
    PRODUCT_REQUEST_TOOL,
    McpProductFailure,
    McpProductInvocation,
    McpProductProvenanceError,
    McpSkillRegistry,
    McpSkillUnregistered,
    ProducerDoesNotOffer,
    ProducerOffer,
    ProducerRegistration,
    ProductQuestion,
    dispatch_skill,
    question_identity,
    verify_mcp_product_failure,
)

ASKED_AT = datetime(2026, 3, 2, 12, 0, tzinfo=UTC)
TENANT = "consumer-tenant"
SERVER = "a-producer"


def entry(product_class: str = "fixture.child-product", version: str = "1.0.0") -> SkillCatalogEntry:
    return SkillCatalogEntry(
        schema_version="1.0.0",
        artifact_version="1.0.0",
        name="ask-a-producer",
        tenant=TENANT,
        skill_type="mcp_product",
        description="asks a registered producer",
        argument_schema=SkillArgumentSchema(properties={}, required=()),
        binding=McpProductBinding(server=SERVER, product_class=product_class, product_version=version),
        requirements=SkillRequirements(required_scopes=frozenset(), required_context_products=frozenset()),
        produces=product_class,
    )


def registration(*, offered: str = "fixture.child-product", floor: str = "1.0.0") -> ProducerRegistration:
    return ProducerRegistration(
        server=SERVER,
        producer_id="producer-x",
        producer_tenant="producer-tenant",
        offers=(ProducerOffer(product_class=offered, versions_from=floor),),
        artifact_address="a" * 64,
    )


def question(**overrides: Any) -> ProductQuestion:
    values: dict[str, Any] = {
        "subject": "acct-1",
        "intent": "fixture-intent",
        "freshness": "fixture-freshness",
        "asked_at": ASKED_AT,
        "parameters": {"revenue_threshold": 1000},
        "request_json": '{"parameters":{"revenue_threshold":1000},"product_id":"fixture.child-product","temporal_boundary":"2026-03-02T12:00:00.000000Z"}',
    }
    values.update(overrides)
    return ProductQuestion(**values)


class _Client:
    def __init__(self, answer: str | Exception) -> None:
        self._answer = answer
        self.calls: list[tuple[str, Mapping[str, Any]]] = []

    def call_tool_text(self, name: str, arguments: Mapping[str, Any]) -> str:
        self.calls.append((name, dict(arguments)))
        if isinstance(self._answer, Exception):
            raise self._answer
        return self._answer


def registry_with(client: Any, reg: ProducerRegistration | None = None) -> McpSkillRegistry:
    registry = McpSkillRegistry(audit_log=AuditLog(), clock=lambda: ASKED_AT)
    registry.register_producer(client=client, registration=reg or registration())
    return registry


def test_the_tool_asked_is_the_doors_own() -> None:
    """dispatch spells the name to stay below ccf.products; this holds the two equal."""
    assert PRODUCT_REQUEST_TOOL == DOOR_TOOL == "request_context_product"


def test_an_mcp_product_entry_is_dispatched_with_a_question_or_not_at_all() -> None:
    registry = registry_with(_Client("{}"))
    with pytest.raises(TypeError, match="ProductQuestion"):
        dispatch_skill(entry(), arguments={}, callable_registry=CallableRegistry(), mcp_skills=registry)
    with pytest.raises(McpSkillUnregistered):
        dispatch_skill(entry(), arguments={}, callable_registry=CallableRegistry(), mcp_skills=None, question=question())


def test_every_argument_the_producer_receives_has_one_source() -> None:
    """tenant from the registration; class and lane from the binding; the instant
    and the four axes from the question; the canonical request verbatim."""
    client = _Client('{"outcome": "x"}')
    result = dispatch_skill(
        entry(), arguments={}, callable_registry=CallableRegistry(), mcp_skills=registry_with(client), question=question()
    )
    assert isinstance(result, McpProductInvocation)
    (name, arguments), = client.calls
    assert name == PRODUCT_REQUEST_TOOL
    assert arguments["tenant"] == "producer-tenant"
    assert arguments["product_class"] == "fixture.child-product" and arguments["version"] == "1.0.0"
    assert arguments["subject"] == "acct-1" and arguments["intent"] == "fixture-intent"
    assert arguments["freshness"] == "fixture-freshness"
    assert arguments["asked_at"] == ASKED_AT.isoformat()
    assert arguments["parameters"] == {"revenue_threshold": 1000}
    assert arguments["request"] == question().request_json
    assert set(arguments) == {"tenant", "product_class", "version", "request", "subject", "intent", "freshness", "asked_at", "parameters"}
    # The invocation carries the registration, the question's identity, and no address.
    assert result.producer_id == "producer-x" and result.producer_tenant == "producer-tenant"
    assert result.producer_registration_address == "a" * 64
    assert result.question_address == question().address
    assert not any("://" in str(v) for v in result.arguments.values())


def test_the_question_identity_binds_every_axis() -> None:
    base = question().address
    assert question(subject="acct-2").address != base
    assert question(intent="other-intent").address != base
    assert question(freshness="other-freshness").address != base
    assert question(asked_at=datetime(2026, 3, 2, 13, 0, tzinfo=UTC)).address != base
    assert question(request_json='{"parameters":{"revenue_threshold":2000},"product_id":"fixture.child-product","temporal_boundary":"2026-03-02T12:00:00.000000Z"}').address != base
    # The same instant in another offset spelling is the same question.
    same_instant = ASKED_AT.astimezone(__import__("datetime").timezone(__import__("datetime").timedelta(hours=2)))
    assert question(asked_at=same_instant).address == base
    assert question_identity(
        request_json=question().request_json, subject="acct-1", intent="fixture-intent",
        freshness="fixture-freshness", asked_at=ASKED_AT,
    ) == base


@pytest.mark.parametrize(
    "raised, kind, detail_fragment",
    [
        (McpTimeout("deadline"), "timeout", "McpTimeout"),
        (McpServerUnreachable("down"), "unreachable", "McpServerUnreachable"),
        (McpToolFailed(PRODUCT_REQUEST_TOOL, "Error executing tool request_context_product: ccf-runtime-failure:" + "ab" * 16), "tool-error", "ccf-runtime-failure:" + "ab" * 16),
        (McpToolFailed(PRODUCT_REQUEST_TOOL, "Error executing tool: parameters {'secret': 'x'} disagree\nTraceback (most recent call last):\n  File ..."), "tool-error", "parameters"),
    ],
    ids=["timeout", "unreachable", "opaque-id", "prose"],
)
def test_a_producer_that_cannot_answer_is_a_minted_value(raised: Exception, kind: str, detail_fragment: str) -> None:
    result = dispatch_skill(
        entry(), arguments={}, callable_registry=CallableRegistry(), mcp_skills=registry_with(_Client(raised)), question=question()
    )
    assert isinstance(result, McpProductFailure)
    assert result.failure == kind
    assert detail_fragment in result.detail
    assert "Traceback" not in result.detail and "\n" not in result.detail
    assert len(result.detail) <= 240
    assert result.producer_id == "producer-x" and result.question_address == question().address
    assert verify_mcp_product_failure(result) is result
    with pytest.raises(McpProductProvenanceError):
        verify_mcp_product_failure(object.__new__(McpProductFailure))
    with pytest.raises(McpProductProvenanceError):
        McpProductFailure(
            skill_name="x", skill_type="mcp_product", server=SERVER, producer_id="anyone",
            producer_tenant="t", producer_registration_address="h", product_class="c",
            product_version="1.0.0", question_address="q", failure="timeout", detail="d", token=object(),
        )


def test_the_registry_refuses_one_name_for_two_registrations_and_an_unoffered_lane() -> None:
    registry = McpSkillRegistry(audit_log=AuditLog(), clock=lambda: ASKED_AT)
    registry.register_producer(client=_Client("{}"), registration=registration())
    with pytest.raises(ValueError, match="already registered"):
        registry.register_producer(client=_Client("{}"), registration=registration())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(server=SERVER, client=_Client("{}"), resources={"r": "x://y"})  # type: ignore[arg-type]
    with pytest.raises(ProducerDoesNotOffer):
        registry.resolve_producer(McpProductBinding(server=SERVER, product_class="fixture.child-product", product_version="2.0.0"))
    with pytest.raises(ProducerDoesNotOffer):
        registry.resolve_producer(McpProductBinding(server=SERVER, product_class="other.class", product_version="1.0.0"))
    with pytest.raises(McpSkillUnregistered):
        registry.resolve_producer(McpProductBinding(server="nobody", product_class="fixture.child-product", product_version="1.0.0"))
