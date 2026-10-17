# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""SEC-030: an unexpected failure crosses either MCP route only as ``ccf-runtime-failure:<id>``.

Dave, 2026-10-17 00:44 MST: *"Any exception raised while a product is acquiring or resolving data must reach the
caller only as the opaque ``ccf-runtime-failure:<id>``. No raw exception message, type name, or internal text may
cross either the tool route or the address-template route."*

Until this fix the door's fault clause in ``runtime/ccf_runtime/mcp/egress.py::_answer_question`` named four types —
``ValueError``, ``TypeError``, ``LookupError``, ``OSError``. Anything else a resolver raised reached the caller as its
own text, on both routes, and left no record in the door's log. Measured on ``main`` ``0746e701``, and first seen in
SEC-020's deliberate break S4: cp-06C's out-of-scope exception with its ``seam_refusals`` binding missing answered
*"facility 'FAC-5B8418' is outside the requested borrower_scope; …"*.

What these tests hold, on the product tool AND the address-form template:

* the caller receives the opaque id and nothing else — no message, no type name;
* the operator keeps the diagnostics: the same id in the door's log, beside the type names of the whole cause chain
  and the frames, and the raised text in no log record (SEC-024, ``D-IMPL-369`` choice C, unchanged);
* a governed absence is still a governed answer, never the opaque failure;
* structurally, the fault clause masks ``Exception`` — not ``BaseException``, and not a bare ``except`` — and the three
  governed types are handled inside it, around the resolver call, before it is reached.
"""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import Any

import httpx
import pytest
from mcp.shared.exceptions import McpError
from mcp.types import TextResourceContents
from pydantic import AnyUrl

from ccf.products.door import WireRequest
from ccf_runtime.mcp.egress import CCF_FAILURE_PREFIX, PRODUCT_REQUEST_TOOL, ProductNotServable, product_address
from tests.mcp.test_egress_logs_carry_no_caller_values import _server_over
from tests.mcp.test_egress_parameters import (  # noqa: F401 - `assembled` is a fixture
    ASKED_AT,
    FRESHNESS,
    INTENT,
    REQUIRED_PARAMETER,
    SUBJECT,
    _drive_mcp,
    _tool_arguments,
    _tool_operation,
    assembled,
)

EGRESS = Path(__file__).resolve().parents[2] / "runtime" / "ccf_runtime" / "mcp" / "egress.py"
_EGRESS_LOGGER = "ccf_runtime.mcp.egress"
#: The transport's own wrappers, which precede the door's text on each route.
_TOOL_PREFIX = f"Error executing tool {PRODUCT_REQUEST_TOOL}: "
_TEMPLATE_PREFIX = "Error creating resource from template: "
_OPAQUE = re.compile(rf"^{CCF_FAILURE_PREFIX}:([0-9a-f]{{32}})$")

#: One marker, carried by every raised exception's text; it must cross neither the wire nor the log.
CANARY = "CANARY-SEC030-facility-FAC-5B8418-is-outside-the-requested-borrower_scope"


class FacilityOutsideRequestedScope(Exception):
    """cp-06C's out-of-scope exception as a door with no ``seam_refusals`` binding for it meets it (SEC-020 break S4)."""


def _http_status_error() -> httpx.HTTPStatusError:
    request = httpx.Request("POST", f"http://graph.invalid/{CANARY}/v1/fluree/query")
    return httpx.HTTPStatusError(f"Server error '500' for url '{request.url}'", request=request,
                                 response=httpx.Response(500, request=request))


def _chained() -> RuntimeError:
    try:
        raise KeyError(CANARY)
    except KeyError as inner:
        try:
            raise RuntimeError(f"the leg failed: {CANARY}") from inner
        except RuntimeError as outer:
            return outer


#: Exceptions outside the four the door used to mask, and the type names the log must carry for each.
UNEXPECTED: dict[str, tuple[Any, tuple[str, ...]]] = {
    "unbound-seam-exception": (lambda: FacilityOutsideRequestedScope(f"facility {CANARY}"), ("FacilityOutsideRequestedScope",)),
    "runtime-error": (lambda: RuntimeError(CANARY), ("RuntimeError",)),
    "assertion-error": (lambda: AssertionError(CANARY), ("AssertionError",)),
    "http-status-error": (_http_status_error, ("HTTPStatusError",)),
    "chained": (_chained, ("RuntimeError", "KeyError")),
}


def _raising(make: Any) -> Any:
    def resolve(**_: Any) -> object:
        raise make()

    return resolve


def _template_operation(uri: str) -> Any:
    """The address-form template; a failure there arrives as an ``McpError``, returned here as its text."""

    async def operation(session: Any) -> tuple[bool, str]:
        try:
            result = await session.read_resource(AnyUrl(uri))
        except McpError as error:
            return True, str(error)
        return False, "".join(c.text for c in result.contents if isinstance(c, TextResourceContents))

    return operation


def _operation(route: str, assembled: Any) -> Any:
    address = assembled.address
    if route == "tool":
        return _tool_operation(_tool_arguments(address, {REQUIRED_PARAMETER: 11}))
    question = WireRequest(product_id=address.product_class, parameters={REQUIRED_PARAMETER: 11},
                           temporal_boundary=ASKED_AT)
    return _template_operation(product_address(
        tenant=address.tenant, product_class=address.product_class, version=address.version, question=question,
        subject=SUBJECT, intent=INTENT, freshness=FRESHNESS, asked_at=ASKED_AT))


def _door_text(route: str, wire: str) -> str:
    """What the door said, with the transport's own wrapper(s) removed — and nothing else removed."""
    prefix = _TOOL_PREFIX if route == "tool" else _TEMPLATE_PREFIX
    assert wire.startswith(prefix), wire
    while wire.startswith(prefix):
        wire = wire[len(prefix):]
    return wire


@pytest.mark.parametrize("kind", sorted(UNEXPECTED))
@pytest.mark.parametrize("route", ["tool", "template"])
def test_an_unexpected_failure_crosses_as_the_opaque_id_and_nothing_else(
    assembled: Any, tmp_path: Path, caplog: pytest.LogCaptureFixture, route: str, kind: str
) -> None:
    caplog.set_level(logging.DEBUG, logger="")
    make, type_names = UNEXPECTED[kind]
    server = _server_over(_raising(make), assembled, tmp_path)

    is_error, wire = _drive_mcp(server, _operation(route, assembled))

    assert is_error is True, wire
    said = _door_text(route, wire)
    opaque = _OPAQUE.match(said)
    assert opaque, f"the door said {said!r}; only {CCF_FAILURE_PREFIX}:<32 hex> may cross"
    assert CANARY not in wire
    for name in type_names:
        assert name not in wire, f"the type name {name} crossed"
    # The operator's half: the same id, logged once, with the chain's types and the frames, never the text.
    formatter = logging.Formatter()
    egress = [formatter.format(r) for r in caplog.records if r.name == _EGRESS_LOGGER]
    assert len(egress) == 1, egress
    assert opaque.group(1) in egress[0], "the id on the wire is not the id in the log"
    for name in type_names:
        assert name in egress[0], f"the log does not name {name}: {egress[0]}"
    assert "resolve" in egress[0], f"the log carries no frame from the raising resolver: {egress[0]}"
    leaking = [r.name for r in caplog.records if not r.name.startswith("mcp.client") and CANARY in formatter.format(r)]
    assert not leaking, f"the raised text reached a log record: {leaking}"


@pytest.mark.parametrize("route", ["tool", "template"])
def test_a_governed_absence_is_still_a_governed_answer_never_the_opaque_failure(
    assembled: Any, tmp_path: Path, route: str
) -> None:
    server = _server_over(_raising(lambda: ProductNotServable(f"absent {CANARY}")), assembled, tmp_path)

    is_error, wire = _drive_mcp(server, _operation(route, assembled))

    assert is_error is False, wire
    assert CCF_FAILURE_PREFIX not in wire and CANARY not in wire, wire
    assert '"refusal":{' in wire, wire


def _answer_question() -> ast.FunctionDef:
    tree = ast.parse(EGRESS.read_text(encoding="utf-8"))
    found = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "_answer_question"]
    assert len(found) == 1, found
    return found[0]


def _calls(handler: ast.ExceptHandler, name: str) -> bool:
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == name for n in ast.walk(handler))


def test_the_fault_clause_masks_exception_and_the_governed_types_are_handled_first() -> None:
    """Structural: the clause that mints the opaque id names ``Exception`` — never ``BaseException``, never bare, never a
    shorter tuple — and the three governed types are caught by an inner ``try`` around the resolver call, inside the
    guarded body, so none of them can reach it."""
    function = _answer_question()
    guarded = [node for node in ast.walk(function) if isinstance(node, ast.Try)
               and any(_calls(handler, "_opaque_failure") for handler in node.handlers)]
    assert len(guarded) == 1, "exactly one fault clause mints the opaque id"
    (outer,) = guarded
    fault = [handler for handler in outer.handlers if _calls(handler, "_opaque_failure")]
    assert len(fault) == 1 and fault[0] is outer.handlers[-1], "the fault clause is the outer try's last handler"
    caught = fault[0].type
    assert isinstance(caught, ast.Name) and caught.id == "Exception", ast.dump(caught) if caught else "bare except"
    inner = [node for statement in outer.body for node in ast.walk(statement) if isinstance(node, ast.Try)]
    governed = {handler.type.id for node in inner for handler in node.handlers if isinstance(handler.type, ast.Name)}
    assert {"ProductNotServable", "ErasedContentRefused", "GovernedRefusalRaised"} <= governed, governed
