"""C2-A (b): the stdio product door needs neither advertised address; HTTP and loopback are unchanged.

Dave, 2026-10-08 (``D-IMPL-378``): *"the stdio product door stops requiring the
two advertised addresses (issuer and resource) it never uses on stdio, for
example by supplying its own values as the loopback transport does; ... the HTTP
and loopback paths untouched."*

Why the two can go on stdio and nowhere else
--------------------------------------------
On HTTP the issuer and resource-server addresses are OAuth discovery metadata:
the protected-resource document a client fetches and the ``resource_metadata``
hint on a 401. No token check and no authorization decision reads either one —
:meth:`~ccf_runtime.mcp.auth.SourceBackedTokenVerifier.verify_token` looks the
token up in the deployment's own source, and
:class:`~ccf_runtime.mcp.tenancy.TenantGuardedServer` decides from the verified
grant and the pinned scope mapping. On stdio ``FastMCP`` builds no HTTP app, so
nothing advertises them at all; the door built them only because the egress
builder takes them together with the token verifier.

What is asserted
----------------
1. **A stdio door spawned with both address variables unset starts and answers.**
   It lists exactly the product tool and serves one governed question, asserting
   the producer identity its ``door:`` section declares. Red before the change:
   the door stopped with ``EnvironmentMissing`` before serving anything.
2. **The same door, still with both unset, refuses what it must**: a call naming
   another tenant (the tenancy guard) and a call for a class its scope mapping
   does not cover (the authorizer). Neither refusal consults an address.
3. **Controls that hold before and after.** A self-hosted HTTP mount still
   requires both addresses and advertises exactly what it is given, and still
   refuses an unauthenticated request. The loopback transport still advertises
   its own bound address and still refuses an unauthenticated request.
"""

from __future__ import annotations

import asyncio
import inspect
import os
import pathlib
import sys
import tempfile
from typing import Any, TextIO

import httpx
import pytest
import yaml
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, TextContent
from pydantic import ValidationError
from starlette.testclient import TestClient

from ccf.client.codec import decode_outcome
from ccf.contracts.canonical import canonical_bytes
from ccf.deployment.environment import EnvironmentDocument
from ccf.products.door import PRODUCT_REQUEST_TOOL, ProducerAssertion, WireRequest
from ccf_runtime.mcp.product_door import ProductDoor, open_door
from tests.mcp.test_product_door_composition import _Product
from tests.products.paved_fixture import (
    ASKED_AT,
    CHILD_CLASS,
    CHILD_VERSION,
    PRODUCER_ID,
    PRODUCER_TENANT,
    THRESHOLD_PARAMETER,
    producer_environment_text,
)
from tests.products.test_paved_consumer import DEV_TOKEN, _producer

pytestmark = [pytest.mark.crossproc]

#: The fixture producer's door program: loopback by default, stdio with ``--stdio``.
DOOR = pathlib.Path(__file__).resolve().parents[1] / "crossproc" / "servers" / "paved_fixture_door.py"

#: The two variables the fixture's environment document names for the
#: addresses, read from that document rather than restated here.
_NAMES = EnvironmentDocument.model_validate(yaml.safe_load(producer_environment_text())).door
assert _NAMES is not None
ADDRESS_VARIABLES = (_NAMES.issuer_url.from_env, _NAMES.resource_server_url.from_env)

#: The question every call below asks, as a client puts it on the wire.
WIRE = WireRequest(product_id=CHILD_CLASS, parameters={THRESHOLD_PARAMETER: 1000}, temporal_boundary=ASKED_AT)


def _arguments(**overrides: Any) -> dict[str, Any]:
    """The product tool's nine arguments for :data:`WIRE`, with ``overrides`` applied."""
    arguments: dict[str, Any] = {
        "tenant": PRODUCER_TENANT,
        "product_class": CHILD_CLASS,
        "version": CHILD_VERSION,
        "request": canonical_bytes(WIRE).decode("utf-8"),
        "subject": "acct-1",
        "intent": "fixture-intent",
        "freshness": "fixture-freshness",
        "asked_at": ASKED_AT.isoformat(),
        "parameters": {THRESHOLD_PARAMETER: 1000},
    }
    arguments.update(overrides)
    return arguments


def _text(result: CallToolResult) -> str:
    return " ".join(block.text for block in result.content if isinstance(block, TextContent))


def _stderr_tail(errlog: TextIO, *, lines: int = 12) -> str:
    errlog.seek(0)
    written = [line for line in errlog.read().splitlines() if line.strip()]
    return "\n".join(written[-lines:])


async def _ask_over_stdio(
    environment: dict[str, str], calls: list[dict[str, Any]], errlog: TextIO
) -> tuple[list[str], list[CallToolResult]]:
    """Spawn the stdio door the way an MCP client does, list it, and make ``calls``."""
    parameters = StdioServerParameters(command=sys.executable, args=[str(DOOR), "--stdio"], env=environment)
    async with stdio_client(parameters, errlog=errlog) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = [tool.name for tool in (await session.list_tools()).tools]
            results = [await session.call_tool(PRODUCT_REQUEST_TOOL, call) for call in calls]
    return tools, results


def test_a_stdio_door_with_both_addresses_unset_starts_answers_and_still_refuses() -> None:
    """C2-A (b). Both variables absent from the child's environment, as a client leaves them."""
    environment = {name: value for name, value in os.environ.items() if name not in ADDRESS_VARIABLES}
    assert not set(ADDRESS_VARIABLES) & set(environment), "an address variable reached the child"

    calls = [
        _arguments(),
        _arguments(tenant="another-tenant"),
        _arguments(product_class="fixture.outside-the-scope-mapping"),
    ]
    with tempfile.TemporaryFile(mode="w+") as errlog:
        try:
            tools, (served, other_tenant, outside_mapping) = asyncio.run(
                _ask_over_stdio(environment, calls, errlog)
            )
        except Exception as unreachable:
            raise AssertionError(
                "the stdio door did not start and answer with both advertised"
                f" addresses unset: {type(unreachable).__name__}: {unreachable}\n"
                f"--- the door's stderr ---\n{_stderr_tail(errlog)}"
            ) from unreachable

    assert tools == [PRODUCT_REQUEST_TOOL], tools

    assert not served.isError, _text(served)
    decoded = decode_outcome(_text(served).encode("utf-8"), sent=WIRE)
    assert decoded.outcome.refusal is None, decoded.outcome.refusal
    assert decoded.outcome.content_address is not None and len(decoded.outcome.content_address) == 64
    assert decoded.outcome.producer == ProducerAssertion(producer_id=PRODUCER_ID, tenant_id=PRODUCER_TENANT)

    # The tenancy guard: the ambient stdio grant holds exactly the door's tenant.
    assert other_tenant.isError, _text(other_tenant)
    assert "does not carry tenant 'another-tenant'" in _text(other_tenant), _text(other_tenant)

    # The authorizer, under the scope mapping the door registered and pinned.
    assert outside_mapping.isError, _text(outside_mapping)
    assert "tenant-unauthorized" in _text(outside_mapping), _text(outside_mapping)
    assert "against the scope mapping in force" in _text(outside_mapping), _text(outside_mapping)


# --- controls: the two transports that DO advertise the addresses ----------------------


def test_the_http_mount_requires_both_addresses_and_advertises_exactly_what_it_is_given(
    tmp_path: pathlib.Path,
) -> None:
    """A deployment hosting ``ProductDoor.server`` itself names both; nothing supplies them."""
    signature = inspect.signature(ProductDoor.server)
    for name in ("issuer_url", "resource_server_url"):
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, name
        assert parameter.default is inspect.Parameter.empty, f"{name} gained a default"

    door = open_door(_Product(tmp_path), environ={"DOOR_TOKEN": "http-control-token"})
    with pytest.raises(TypeError):
        door.server()  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        door.server(issuer_url="", resource_server_url="")

    issuer, resource = "https://issuer.http-control.invalid/", "https://door.http-control.invalid/mcp"
    server = door.server(issuer_url=issuer, resource_server_url=resource)
    assert server.settings.auth is not None
    assert (str(server.settings.auth.issuer_url), str(server.settings.auth.resource_server_url)) == (issuer, resource)

    with TestClient(server.streamable_http_app()) as client:
        metadata = client.get("/.well-known/oauth-protected-resource/mcp")
        assert metadata.status_code == 200, metadata.text
        assert (metadata.json()["resource"], metadata.json()["authorization_servers"]) == (resource, [issuer])
        refused = client.post("/mcp", json={})
        assert refused.status_code == 401, refused.text
        assert (
            'resource_metadata="https://door.http-control.invalid/.well-known/oauth-protected-resource/mcp"'
            in refused.headers["www-authenticate"]
        ), refused.headers


def test_the_loopback_door_advertises_its_own_address_and_refuses_without_a_token() -> None:
    """The loopback transport derives its addresses from the port it binds, as before."""
    with _producer() as url, httpx.Client(trust_env=False, timeout=10) as client:
        origin = url.removesuffix("/mcp")
        metadata = client.get(f"{origin}/.well-known/oauth-protected-resource/mcp")
        assert metadata.status_code == 200, metadata.text
        assert (metadata.json()["resource"], metadata.json()["authorization_servers"]) == (url, [f"{origin}/"])
        refused = client.post(url, json={})
        assert refused.status_code == 401, refused.text
        assert (
            f'resource_metadata="{origin}/.well-known/oauth-protected-resource/mcp"'
            in refused.headers["www-authenticate"]
        ), refused.headers
        authorized = client.post(
            url,
            json={},
            headers={"Authorization": f"Bearer {DEV_TOKEN}", "Accept": "application/json, text/event-stream"},
        )
        assert authorized.status_code != 401, "the loopback door refused its own credential"
