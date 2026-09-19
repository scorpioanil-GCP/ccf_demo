"""cp-06's governed product over MCP — driven, not merely declared.

**This module exists because two defects shipped in that door and no test could
see them.** cp-06 went through `D-GATE-cp-06` carrying `server/door.yaml`,
`server/serve.py`, and a test asserting the door *declares* a `module:callable`
entry point — a static read of the YAML. **Nothing ever booted it.** Measured
2026-09-10 by driving the shipped door with the shipped cp-04 driver:

* `CP07-F-08` — the assembly root was named and never created, so the first call
  answered `unable to open database file`;
* `CP07-F-09` — the hand-rolled `RefusalEnvelope` could not be constructed, so a
  governed "no" reached the caller as `ccf-runtime-failure:<id>`.

Both were found while building cp-07's door, which inherited the same code
shape. A door that has never been opened passes every test written about its
declaration, so the guard is the opening.

**ENV-GATED, deliberately.** cp-06 assembles from a live Fluree ledger and a
live Postgres estate; this skips unless the deployment's own four variables are
set. **The driver is cp-04's**, imported rather than reimplemented.
"""

from __future__ import annotations

import ast
import importlib
import json
import os
import pathlib
import sys
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.products.door import WireRequest

from tests.examples.test_cp_04_two_callers import drive, tool_call

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-06-collateral-and-setoff-coverage"
SERVER = EXAMPLE / "server"

REQUIRED_ENV = (
    "CCF_CP_06_FLUREE_URL",
    "CCF_CP_06_FLUREE_LEDGER",
    "CCF_CP_06_POSTGRES_DSN",
    "CCF_CP_06_POSTGRES_SCHEMA",
)

pytestmark = pytest.mark.skipif(
    any(not os.environ.get(name) for name in REQUIRED_ENV),
    reason=(
        "cp-06's MCP door assembles from the live estate; set "
        + ", ".join(REQUIRED_ENV)
        + " to run it"
    ),
)


def _anchor(name: str) -> str:
    """A demonstration constant, read from `run.py` rather than restated."""
    for node in ast.walk(ast.parse((EXAMPLE / "run.py").read_text(encoding="utf-8"))):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return str(ast.literal_eval(node.value))
    raise AssertionError(f"run.py declares no {name}")


def _load(name: str) -> Any:
    """Import one of cp-06's modules, with the example's own two roots first."""
    wanted = [str(EXAMPLE), str(SERVER)]
    if sys.path[:2] != wanted:
        for entry in wanted:
            while entry in sys.path:
                sys.path.remove(entry)
        for entry in reversed(wanted):
            sys.path.insert(0, entry)
    for module in ("acquisition", "deployment", "produce", "projection", "serve"):
        sys.modules.pop(module, None)
    return importlib.import_module(name)


def _arguments(*, asked_at: datetime, anchored: bool = True,
               **overrides: Any) -> dict[str, Any]:
    """cp-06's question, as the product tool's arguments.

    The encoded `request` and the `parameters` argument must agree: a call whose
    two halves disagree is refused as malformed before any governance runs
    (C-01), which would measure the wire rather than the door.
    """
    dep = _load("deployment")
    config = dep.config()
    schema_name = config["product_class"]["schema_name"]

    parameters: dict[str, Any] = {}
    if anchored:
        parameters = {
            dep.FACILITY: _anchor("DEMONSTRATION_FACILITY"),
            dep.BORROWER_SCOPE: [_anchor("DEMONSTRATION_SCOPE")],
        }
    parameters.update(overrides)

    wire = WireRequest(
        product_id=schema_name, parameters=parameters, temporal_boundary=asked_at
    )
    return {
        "tenant": config["tenant_id"],
        "product_class": schema_name,
        "version": str(config["product_class"]["schema_version"]),
        "request": canonical_bytes(wire).decode("utf-8"),
        "subject": parameters.get(dep.FACILITY, ""),
        "intent": "lgd-assessment",
        "freshness": "standard",
        "asked_at": asked_at.isoformat(),
        "parameters": parameters,
    }


@pytest.fixture(scope="module")
def outcomes() -> dict[str, Any]:
    """Every branch, over ONE door, in ONE lifespan."""
    serve = _load("serve")
    instant = datetime.now(UTC)
    with tempfile.TemporaryDirectory(prefix="cp06-door-") as scratch:
        with serve.door(root=pathlib.Path(scratch)) as opened:
            return drive(
                opened,
                {
                    # NO allocation basis — the class default is the authority.
                    "default": tool_call(_arguments(asked_at=instant)),
                    "pro_rata": tool_call(
                        _arguments(asked_at=instant, shared_collateral="pro-rata")),
                    "no_anchor": tool_call(
                        _arguments(asked_at=instant, anchored=False)),
                },
            )


def _payload(outcomes: dict[str, Any], key: str) -> dict[str, Any]:
    is_error, text = outcomes[key]
    assert not is_error, text
    body = json.loads(text)
    assert body["content_address"], f"{key} crossed MCP with no content address"
    assert body["replay_ref"], f"{key} crossed MCP with no replay reference"
    return json.loads(body["product_json"])["payload"]


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_the_door_answers_its_first_call(outcomes: Any) -> None:
    """`CP07-F-08`, and the assertion is deliberately the plainest one possible.

    The shipped door returned `unable to open database file` here — an MCP
    transport error indistinguishable from a producer that never started,
    because `deployment.connection` hands SQLite a path inside a directory
    nothing created. A governed product crossing the wire at all is the whole
    claim.
    """
    payload = _payload(outcomes, "default")
    assert payload["coverage"]["coverage_ratio"]
    assert payload["assets"], "the door served a facility with no collateral"


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_a_caller_supplied_basis_reaches_the_projection_over_mcp(
    outcomes: Any
) -> None:
    """The two allocation bases must disagree across the wire too.

    Which is larger is a fact about the estate rather than about the code and is
    not asserted; that they DIFFER is what proves the parameter survived the
    transport and reached Π rather than being dropped into a default.
    """
    default = Decimal(_payload(outcomes, "default")["coverage"]["coverage_ratio"])
    pro_rata = Decimal(_payload(outcomes, "pro_rata")["coverage"]["coverage_ratio"])
    assert pro_rata != default


def test_a_question_with_no_anchor_is_refused_by_GOVERNANCE(outcomes: Any) -> None:
    """`CP07-F-09` — and the door refuses none of it.

    `facility_id` and `borrower_scope` are `required` in the request contract,
    so the Control Plane is what says no, with a kind from the SDK's own
    vocabulary and a replay reference. The shipped door hand-rolled this refusal
    with fields `RefusalEnvelope` does not declare; the constructor raised and
    the caller received `ccf-runtime-failure:<id>`, which the SDK reserves for
    *"CCF or its runtime failed"*.

    The KIND is asserted, not merely the presence of a refusal: a refusal whose
    kind flattened would be a well-formed envelope carrying the wrong answer.
    """
    is_error, text = outcomes["no_anchor"]
    assert not is_error, (
        "a governed refusal arrived as a transport error; a determination the"
        f" fabric made is a successful response: {text}"
    )
    body = json.loads(text)
    assert body["product_json"] is None, "a question with no anchor served a product"
    assert body["content_address"] is None
    refusal = body["refusal"]
    assert refusal["kind"] == "product-request-violation", refusal["kind"]
    presented = json.loads(refusal["fields"]["presented_keys"])
    declared = json.loads(refusal["fields"]["declared_keys"])
    assert "facility_id" in declared and "facility_id" not in presented
    assert body["replay_ref"], (
        "the refused branch crossed MCP with no replay reference; a door that"
        " cannot record a refusal is not a governed door (`D-IMPL-256`)"
    )


def test_the_door_reimplements_no_governance() -> None:
    """Measured off the shipped file rather than asserted in prose.

    The names below are the governed path: if any appears in the door, the door
    has become a second governance authority and the deployment now has two
    answers to the same question.
    """
    source = (SERVER / "serve.py").read_text(encoding="utf-8")
    for forbidden in ("run_gates", "build_replay_record", "ProjectionEngine",
                      "assess_debt", "build_governed_resolver"):
        assert forbidden not in source, (
            f"server/serve.py names {forbidden!r}; the door must translate and"
            " delegate, never re-decide"
        )
    assert "produce.assemble_and_serve" in source
