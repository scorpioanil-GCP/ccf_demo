"""The standard door's product RESOURCE is guarded exactly as its tool is (round 5, item 2).

**SDK-defined** (CLAUDE.md §7.1, §8.3). Dave, 2026-10-11 20:19 MST: *"Registering
a product resource must not create an unguarded retrieval path."*

Until this round :class:`~ccf_runtime.mcp.product_door.ProductDoor` passed
``expose_product_resource=False`` unconditionally, so a deployment whose ruled
gate requires the resource to be registered and enumerable (cp-04's
``CFT-G13``) had no supported way to keep it on the standard door. The door now
takes ``expose_product_resource=True`` at open. Held here, over the real MCP
door (ASGI, real bearer verification), in one module:

* by default the resource template is NOT registered (unchanged);
* opened with the flag, the template is enumerable;
* a principal with a valid credential and NO entitlement is refused on the
  resource exactly as on the tool — ``principal-not-entitled`` on the record,
  no product delivered on either surface;
* a declared principal reaches the resource's resolver (no entitlement refusal
  on its record);
* an unknown credential is refused at the verifier on both surfaces.
"""

from __future__ import annotations

import asyncio
import inspect
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from mcp.types import TextContent

from ccf.contracts.canonical import canonical_bytes
from ccf.client.wire import WireRequest
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.mcp.client import run_with_session
from ccf.mcp.errors import McpServerUnreachable
from ccf.products.contract import SUBJECT_WITHHOLDING_NEVER
from ccf.products.product import open_product
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource, TokenGrant
from ccf_runtime.mcp.egress import PRODUCT_REQUEST_TOOL, PRODUCT_URI_TEMPLATE, product_uri
from ccf_runtime.mcp.product_door import open_door_with_verifier

from tests.composition import declare_wide_temporal_boundary, declared_erasure_trust
from tests.products import paved_fixture as fixture

DECLARED = "principal-declared"
UNDECLARED = "principal-undeclared"
ROLE = "role-declared"
BASE_URL = "http://127.0.0.1:8139"


def _open(tmp_path: Path) -> Any:
    root = fixture.write_tree(
        tmp_path / "deployment",
        config=fixture.producer_config(
            subject_withholding=SUBJECT_WITHHOLDING_NEVER,
            product_entitlement={
                "tenant_id": fixture.PRODUCER_TENANT,
                "policy_version": fixture.CHILD_VERSION,
                "principals": {
                    DECLARED: {"permitted_schema_names": [fixture.CHILD_CLASS], "permitted_roles": [ROLE]},
                },
            },
        ),
        environment=fixture.producer_environment_text(),
    )
    control_plane = ControlPlaneRegistry()
    declare_wide_temporal_boundary(control_plane, tenant_id=fixture.PRODUCER_TENANT)
    return open_product(
        erasure_trust=declared_erasure_trust(fixture.PRODUCER_TENANT),
        config_root=root,
        scratch=tmp_path / "scratch",
        acquire=fixture.Acquire(),
        project=fixture.plan_factory,
        assess=fixture.assess,
        environ={fixture.CHILD_DSN_VAR: "postgresql://fixture"},
        control_plane=control_plane,
    )


def _door(opened: Any, *, resource: bool) -> Any:
    """The standard door with the deployment's own verifier; the resource only when asked.

    The flag is passed only when the door accepts it, so on an SDK without it this
    module fails by ASSERTION (the template is absent), not by a ``TypeError``.
    """
    scope = opened.door.required_scope
    tenants = frozenset({opened.tenant_id})
    source = StaticTokenSource(
        grants={
            f"token-{principal}": TokenGrant(client_id=principal, scopes=(scope,), tenants=tenants)
            for principal in (DECLARED, UNDECLARED)
        }
    )

    def resolve(*, grant: TokenGrant, tenant: str, requested_role: str | None) -> Perspective:
        del tenant, requested_role
        return Perspective(principal_id=grant.client_id, role=ROLE)

    extra: dict[str, Any] = {}
    if resource and "expose_product_resource" in inspect.signature(open_door_with_verifier).parameters:
        extra["expose_product_resource"] = True
    return open_door_with_verifier(
        opened,
        environ={fixture.CREDENTIAL_VAR: "door-boot-token"},
        token_verifier=SourceBackedTokenVerifier(source=source),
        perspective_resolver=resolve,
        **extra,
    )


def _drive(door: Any, token: str, operation: Any) -> dict[str, Any]:
    app = door.server(
        issuer_url="https://issuer.invalid", resource_server_url=f"{BASE_URL}/mcp"
    ).streamable_http_app()

    async def go() -> Any:
        async with app.router.lifespan_context(app):

            def factory() -> httpx.AsyncClient:
                return httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url=BASE_URL,
                    headers={"Authorization": f"Bearer {token}"},
                )

            try:
                return await run_with_session(
                    url=f"{BASE_URL}/mcp", operation=operation, http_client_factory=factory
                )
            except McpServerUnreachable as refused:
                return {"unreachable": str(refused)}

    return asyncio.run(go())


def _templates(door: Any) -> list[str]:
    async def operation(session: Any) -> Any:
        listed = await session.list_resource_templates()
        return {"templates": [t.uriTemplate for t in listed.resourceTemplates]}

    outcome = _drive(door, f"token-{DECLARED}", operation)
    assert "templates" in outcome, f"the listing did not answer at all: {outcome}"
    return outcome["templates"]


def _read(door: Any, opened: Any, token: str) -> dict[str, Any]:
    uri = product_uri(tenant=opened.tenant_id, product_class=fixture.CHILD_CLASS, version=fixture.CHILD_VERSION)

    async def operation(session: Any) -> Any:
        result = await session.read_resource(uri)
        return {"text": " | ".join(getattr(c, "text", "") for c in result.contents)}

    return _drive(door, token, operation)


def _call(door: Any, opened: Any, token: str) -> dict[str, Any]:
    now = datetime.now(UTC)
    parameters = {fixture.THRESHOLD_PARAMETER: 1000}
    arguments = {
        "tenant": opened.tenant_id,
        "product_class": fixture.CHILD_CLASS,
        "version": fixture.CHILD_VERSION,
        "request": canonical_bytes(
            WireRequest(product_id=fixture.CHILD_CLASS, parameters=parameters, temporal_boundary=now)
        ).decode("utf-8"),
        "subject": "acct-1",
        "intent": "fixture-intent",
        "freshness": "fixture-freshness",
        "asked_at": now.isoformat(),
        "parameters": parameters,
    }

    async def operation(session: Any) -> Any:
        result = await session.call_tool(PRODUCT_REQUEST_TOOL, arguments)
        return {
            "is_error": bool(result.isError),
            "text": " | ".join(c.text for c in result.content if isinstance(c, TextContent)),
        }

    return _drive(door, token, operation)


def _record(opened: Any, reference: str) -> DecisionReplayRecord:
    store = opened.artifact_store
    return DecisionReplayRecord.model_validate_json(
        store.get(content_address=store.resolve_uri(uri=reference))
    )


def _resource_refusal_reference(outcome: dict[str, Any]) -> str:
    """The replay reference a resource read's refusal shell carries, or fail."""
    assert "text" in outcome, f"the resource read did not answer at all: {outcome}"
    body = json.loads(outcome["text"])
    assert body.get("kind") is not None, f"the resource read returned no refusal shell: {body}"
    return str(body["replay_reference"])


# --- registration --------------------------------------------------------------------------


def test_by_default_the_standard_door_registers_no_product_resource(tmp_path: Path) -> None:
    with _open(tmp_path) as opened:
        assert PRODUCT_URI_TEMPLATE not in _templates(_door(opened, resource=False))


def test_opened_with_the_flag_the_product_resource_is_enumerable(tmp_path: Path) -> None:
    with _open(tmp_path) as opened:
        templates = _templates(_door(opened, resource=True))
        assert PRODUCT_URI_TEMPLATE in templates, templates


# --- the guard: the resource refuses exactly as the tool does -------------------------------


def test_an_unentitled_principal_is_refused_on_the_resource_exactly_as_on_the_tool(tmp_path: Path) -> None:
    with _open(tmp_path) as opened:
        door = _door(opened, resource=True)

        on_tool = _call(door, opened, f"token-{UNDECLARED}")
        tool_body = json.loads(on_tool["text"])
        assert tool_body.get("refusal") is not None and not tool_body.get("content_address"), on_tool
        tool_record = _record(opened, tool_body["replay_ref"])

        on_resource = _read(door, opened, f"token-{UNDECLARED}")
        resource_record = _record(opened, _resource_refusal_reference(on_resource))

        # The same entitlement decision, by name, on both records; no product on either.
        assert "principal-not-entitled" in tool_record.content_generation_path.assembly_refusal
        assert "principal-not-entitled" in resource_record.content_generation_path.assembly_refusal
        assert resource_record.perspective_conditioning.principal_id == UNDECLARED
        assert "content_address" not in json.loads(on_resource["text"])


def test_a_declared_principal_passes_the_resource_entitlement(tmp_path: Path) -> None:
    """The positive control: the guard admits the entitled principal to the RESOLVER.

    The paved fixture is a parameterized class, so its resolver has no standing
    answer for a request-less read and says so by name
    (``ProductNotResolvable``, ``src/ccf/products/product.py::OpenedProduct.resolve``).
    Reaching that sentence is the proof the entitlement admitted the caller: an
    unentitled caller is answered by the door's refusal shell before the
    resolver is ever called (the test above).
    """
    with _open(tmp_path) as opened:
        door = _door(opened, resource=True)
        outcome = _read(door, opened, f"token-{DECLARED}")
        assert "parameterized class with no standing answer" in outcome.get("unreachable", ""), outcome


def test_an_unknown_credential_is_refused_on_the_resource_and_on_the_tool(tmp_path: Path) -> None:
    with _open(tmp_path) as opened:
        door = _door(opened, resource=True)
        on_resource = _read(door, opened, "token-nobody-issued")
        on_tool = _call(door, opened, "token-nobody-issued")
        assert "401" in on_resource.get("unreachable", ""), on_resource
        assert "401" in on_tool.get("unreachable", ""), on_tool
