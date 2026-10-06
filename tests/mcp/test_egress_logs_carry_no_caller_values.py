"""SEC-024: validation errors and egress door messages carry no caller values into logs.

``D-IMPL-368``, row ``SEC-024`` of
``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``. The ruled
fix shape is *"log types and locations, not values"*:

(i)   ``src/ccf/contracts/base.py::CCFContract`` sets ``hide_input_in_errors``,
      so a pydantic ``ValidationError``'s ``str()``/``repr()`` no longer carries
      ``input_value``;
(ii)  ``runtime/ccf_runtime/mcp/egress.py::_opaque_failure`` renders, for the
      whole ``__cause__``/``__context__`` chain, only exception TYPE NAMES and
      traceback FRAMES — never ``str()``/``repr()`` of an exception;
(iii) the door's own ``ValueError`` messages carry keys and locations, never
      values (the pattern ``src/ccf/graph/registry.py::_connection_refusal``
      already uses).

Every canary is placed in a field **value**, never in a key: ``extra_forbidden``
reports the key in ``loc``, which hiding does not touch, so a canary-as-key
would be a false red.

Case 2b is an addition beyond the row's three named cases: it drives
``_opaque_failure`` through the one path that reaches it on this tree (a
resolver failure inside ``_answer_question``'s guarded block), with a canary in
the exception TEXT, so severing (b) — restoring ``exc_info=exc`` rendering —
has a test that measures exactly that rendering.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl, ValidationError

from ccf.contracts.base import CCFContract
from ccf.projection.plan import Perspective
from ccf.products.request import ProductRequest
from ccf_runtime.mcp import tenancy
from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier
from ccf_runtime.mcp.egress import (
    CCF_FAILURE_PREFIX,
    PRODUCT_REQUEST_TOOL,
    build_egress_server,
)
from tests.mcp.guarded_servers import wide_authorizer
from tests.mcp.test_egress_parameters import (  # noqa: F401 - `assembled` is a fixture
    IN_PROCESS_BASE_URL,
    REQUIRED_PARAMETER,
    ROLE,
    SCOPE,
    SERVER_NAME,
    TOKEN,
    TOOL_DESCRIPTION,
    _drive_mcp,
    _entitlement,
    _mcp_server,
    _recorder,
    _token_file,
    _tool_arguments,
    _tool_operation,
    assembled,
)

#: One distinct canary per case, so a red names the case that leaked.
CANARY_CONTRACT = "CANARY-SEC024-CONTRACT-VALUE"
CANARY_MISMATCH = "CANARY-SEC024-MISMATCH-VALUE"
CANARY_DIRECT = "CANARY-SEC024-DIRECT-VALUE"
CANARY_FABRIC = "CANARY-SEC024-FABRIC-FAILURE-TEXT"

#: FastMCP's own wrapper on a tool error is the transport's; what follows it is
#: the door's ToolError text, which must be the opaque id and nothing else
#: (see ``tests/mcp/test_egress_refusal_channels.py::test_a_raised_failure_is_a_tool_error_with_an_opaque_id``).
_FASTMCP_PREFIX = f"Error executing tool {PRODUCT_REQUEST_TOOL}: "
_OPAQUE = re.compile(rf"^{CCF_FAILURE_PREFIX}:[0-9a-f]{{32}}$")


class _CountProbe(CCFContract):
    """A minimal boundary contract with one ``int`` field to feed a string."""

    count: int


def _chain(exc: BaseException) -> list[BaseException]:
    seen: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None and current not in seen:
        seen.append(current)
        current = current.__cause__ or current.__context__
    return seen


def _assert_no_canary_logged(caplog: pytest.LogCaptureFixture, canary: str) -> None:
    assert canary not in caplog.text, caplog.text
    formatter = logging.Formatter()
    for record in caplog.records:
        rendered = formatter.format(record)
        assert canary not in rendered, (record.name, rendered)


def _assert_opaque_wire(text: str) -> None:
    assert text.startswith(_FASTMCP_PREFIX), text
    assert _OPAQUE.match(text[len(_FASTMCP_PREFIX) :]), text


# ---------------------------------------------------------------------------
# (1) The contract base hides the rejected value.
# ---------------------------------------------------------------------------


def test_a_contract_validation_error_hides_the_rejected_value() -> None:
    with pytest.raises(ValidationError) as refused:
        _CountProbe(count=CANARY_CONTRACT)  # type: ignore[arg-type]
    assert CANARY_CONTRACT not in str(refused.value)
    assert CANARY_CONTRACT not in repr(refused.value)
    # The location survives: the error still names WHICH field was refused.
    assert "count" in str(refused.value)


# ---------------------------------------------------------------------------
# (2) Through the egress door: a parameters mismatch logs no caller value.
# ---------------------------------------------------------------------------


def test_the_egress_door_logs_no_caller_value_on_a_parameters_mismatch(
    assembled: Any, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="")
    server = _mcp_server(
        tmp_path, servable=assembled.served, address=assembled.address, carried=[]
    )
    arguments = _tool_arguments(assembled.address, {REQUIRED_PARAMETER: 11})
    arguments["parameters"] = {REQUIRED_PARAMETER: CANARY_MISMATCH}

    is_error, text = _drive_mcp(server, _tool_operation(arguments))

    assert is_error is True, text
    _assert_no_canary_logged(caplog, CANARY_MISMATCH)
    _assert_opaque_wire(text)


# ---------------------------------------------------------------------------
# (2b) The one path that reaches `_opaque_failure`: a fabric failure's TEXT.
# ---------------------------------------------------------------------------


def _failing_resolver(text: str) -> Any:
    def resolve(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> object:
        try:
            raise LookupError(f"inner cause carrying {text}")
        except LookupError as inner:
            raise ValueError(f"outer failure carrying {text}") from inner

    return resolve


def test_the_opaque_failure_log_renders_types_and_frames_not_exception_text(
    assembled: Any, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="")
    server = build_egress_server(
        server_name=SERVER_NAME,
        resolver=_failing_resolver(CANARY_FABRIC),
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(
                path=_token_file(tmp_path, tenant=assembled.address.tenant)
            )
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl(f"{IN_PROCESS_BASE_URL}/mcp"),
            required_scopes=[SCOPE],
        ),
        authorizer=wide_authorizer(scopes=(SCOPE,)),
        entitlement_source=_entitlement(assembled.address),
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role=ROLE
            )
        ),
        refusal_recorder=_recorder(tmp_path, tenant=assembled.address.tenant),
        expose_product_tool=True,
        product_tool_description=TOOL_DESCRIPTION,
    )
    arguments = _tool_arguments(assembled.address, {REQUIRED_PARAMETER: 11})

    is_error, text = _drive_mcp(server, _tool_operation(arguments))

    assert is_error is True, text
    _assert_opaque_wire(text)
    _assert_no_canary_logged(caplog, CANARY_FABRIC)
    # Non-vacuity: the failure WAS logged, with the type names of the whole
    # chain and the frames — an operator still finds what failed and where.
    failures = [r for r in caplog.records if r.name == "ccf_runtime.mcp.egress"]
    assert failures, caplog.text
    rendered = logging.Formatter().format(failures[-1])
    assert "ValueError" in rendered and "LookupError" in rendered, rendered
    assert "_failing_resolver" in rendered or "resolve" in rendered, rendered


# ---------------------------------------------------------------------------
# (3) The mismatch error itself carries no values.
# ---------------------------------------------------------------------------


def test_the_mismatch_error_itself_carries_no_values(
    assembled: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = _mcp_server(
        tmp_path, servable=assembled.served, address=assembled.address, carried=[]
    )
    verifier = SourceBackedTokenVerifier(
        source=FileTokenSource(
            path=_token_file(tmp_path, tenant=assembled.address.tenant)
        )
    )
    token = asyncio.run(verifier.verify_token(TOKEN))
    monkeypatch.setattr(tenancy, "get_access_token", lambda: token)
    arguments = _tool_arguments(assembled.address, {REQUIRED_PARAMETER: 11})
    arguments["parameters"] = {REQUIRED_PARAMETER: CANARY_DIRECT}
    arguments["asked_at"] = datetime.fromisoformat(arguments["asked_at"])
    tool = server._tool_manager.get_tool(PRODUCT_REQUEST_TOOL).fn

    with pytest.raises(ValueError) as refused:
        tool(**arguments)

    for link in _chain(refused.value):
        assert CANARY_DIRECT not in str(link), (type(link).__name__, str(link))
    # The location survives: the refusal still names the axis and the key.
    assert "parameters" in str(refused.value)
    assert REQUIRED_PARAMETER in str(refused.value)
