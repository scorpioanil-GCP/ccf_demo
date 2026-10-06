"""SEC-024: validation errors carry no caller values into logs (choice C).

``D-IMPL-369`` choice C, executed under ``D-IMPL-370``; row ``SEC-024`` of
``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``. The
ruling is *"Logs and CCFContract only. Preserve the client-refusal wire
unchanged."* The fix shape:

(i)   ``src/ccf/contracts/base.py::CCFContract`` sets ``hide_input_in_errors``,
      so a pydantic ``ValidationError``'s ``str()``/``repr()`` no longer carries
      ``input_value``;
(ii)  ``runtime/ccf_runtime/mcp/egress.py::_opaque_failure`` renders, for the
      whole ``__cause__``/``__context__`` chain, only exception TYPE NAMES and
      traceback FRAMES — never ``str()``/``repr()`` of an exception, and never
      through ``exc_info``.

Out of scope by the ruling, and deliberately NOT asserted here: the door's
C-01 refusal messages (parameters, ``product_id`` and temporal mismatches).
They are client wire, raised before the ``try`` that reaches
``_opaque_failure``, and ``tests/mcp/test_egress_parameters.py`` pins their
values on the wire; those tests are this row's regression guard.

Every canary is placed in a field **value**, never in a key: ``extra_forbidden``
reports the key in ``loc``, which hiding does not touch, so a canary-as-key
would be a false red.

Records named ``mcp.client.*`` are excluded from the per-record check: they
are the in-process test client echoing its own outbound request, which no code
in ``src/`` or ``runtime/`` emits or can change.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pytest
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl, ValidationError

from ccf.contracts.base import CCFContract
from ccf.projection.plan import Perspective
from ccf.products.request import ProductRequest
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
    TOOL_DESCRIPTION,
    _drive_mcp,
    _entitlement,
    _recorder,
    _token_file,
    _tool_arguments,
    _tool_operation,
    assembled,
)

#: One distinct canary per case, so a red names the case that leaked.
CANARY_CONTRACT = "CANARY-SEC024-CONTRACT-VALUE"
CANARY_RESOLVER_CONTRACT = "CANARY-SEC024-RESOLVER-CONTRACT-VALUE"
CANARY_FABRIC = "CANARY-SEC024-FABRIC-FAILURE-TEXT"

#: FastMCP's own wrapper on a tool error is the transport's; what follows it is
#: the door's ToolError text, which must be the opaque id and nothing else
#: (see ``tests/mcp/test_egress_refusal_channels.py::test_a_raised_failure_is_a_tool_error_with_an_opaque_id``).
_FASTMCP_PREFIX = f"Error executing tool {PRODUCT_REQUEST_TOOL}: "
_OPAQUE = re.compile(rf"^{CCF_FAILURE_PREFIX}:[0-9a-f]{{32}}$")
_EGRESS_LOGGER = "ccf_runtime.mcp.egress"


class _CountProbe(CCFContract):
    """A minimal boundary contract with one ``int`` field to feed a string."""

    count: int


def _assert_no_canary_logged(caplog: pytest.LogCaptureFixture, canary: str) -> None:
    assert canary not in caplog.text, caplog.text
    formatter = logging.Formatter()
    for record in caplog.records:
        if record.name.startswith("mcp.client"):
            continue
        rendered = formatter.format(record)
        assert canary not in rendered, (record.name, rendered)


def _assert_opaque_wire(text: str) -> None:
    assert text.startswith(_FASTMCP_PREFIX), text
    assert _OPAQUE.match(text[len(_FASTMCP_PREFIX) :]), text


def _egress_failure_record(caplog: pytest.LogCaptureFixture) -> str:
    """The door's own failure record, formatted — non-vacuity for the log cases."""
    failures = [r for r in caplog.records if r.name == _EGRESS_LOGGER]
    assert failures, caplog.text
    return logging.Formatter().format(failures[-1])


def _server_over(resolver: Any, assembled: Any, tmp_path: Path) -> Any:
    return build_egress_server(
        server_name=SERVER_NAME,
        resolver=resolver,
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
# (2) A CCFContract ValidationError raised INSIDE the resolver leaves no value
#     in the log, and the client sees only the opaque id.
# ---------------------------------------------------------------------------


def _contract_refusing_resolver(value: str) -> Any:
    def resolve(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> object:
        return _CountProbe(count=value)  # type: ignore[arg-type]

    return resolve


def test_a_contract_validation_error_inside_the_resolver_logs_no_caller_value(
    assembled: Any, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="")
    server = _server_over(
        _contract_refusing_resolver(CANARY_RESOLVER_CONTRACT), assembled, tmp_path
    )
    arguments = _tool_arguments(assembled.address, {REQUIRED_PARAMETER: 11})

    is_error, text = _drive_mcp(server, _tool_operation(arguments))

    assert is_error is True, text
    _assert_opaque_wire(text)
    _assert_no_canary_logged(caplog, CANARY_RESOLVER_CONTRACT)
    # Non-vacuity: the failure WAS logged, naming the type and a frame.
    rendered = _egress_failure_record(caplog)
    assert "ValidationError" in rendered, rendered
    assert "_contract_refusing_resolver" in rendered or "resolve" in rendered, rendered


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
    server = _server_over(_failing_resolver(CANARY_FABRIC), assembled, tmp_path)
    arguments = _tool_arguments(assembled.address, {REQUIRED_PARAMETER: 11})

    is_error, text = _drive_mcp(server, _tool_operation(arguments))

    assert is_error is True, text
    _assert_opaque_wire(text)
    _assert_no_canary_logged(caplog, CANARY_FABRIC)
    # Non-vacuity: the failure WAS logged, with the type names of the whole
    # chain and the frames — an operator still finds what failed and where.
    rendered = _egress_failure_record(caplog)
    assert "ValueError" in rendered and "LookupError" in rendered, rendered
    assert "_failing_resolver" in rendered or "resolve" in rendered, rendered
