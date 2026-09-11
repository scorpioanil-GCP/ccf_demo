"""cp-07's governed product over MCP — transport, not a second governance path.

The question this module answers is the one every door has to answer: **is MCP
merely a transport over the governed product, or does the author rebuild CCF
semantics at the transport boundary?**

`server/serve.py` carries no governance and no replay logic — it translates an
MCP call into a `ProductRequest`, delegates to `produce.assemble_and_serve`, and
hands back what the fabric decided. This module is the runtime half of that
claim: it drives the SHIPPED door with the SHIPPED driver and asserts that the
things rung 7 is about — the evidence boundary, the truncation disclosure, the
declared gate — survive the wire unchanged.

**A bound the caller omits must stay omitted across the wire.** That is the one
thing a door most easily gets wrong: restating a default in the adapter gives
the deployment a second governance authority, and the two drift silently. So the
default call sends no `limit` at all and the class default is what must resolve.

**ENV-GATED, deliberately.** cp-07 assembles from a live Fluree ledger and a
live Postgres estate; this skips unless the deployment's own four variables are
set.

**The driver is cp-04's**, imported rather than reimplemented: one lifespan, one
credential, each operation in its own session, refusals caught and returned.
"""

from __future__ import annotations

import importlib
import json
import os
import pathlib
import sys
import tempfile
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.products.door import WireRequest

from tests.examples.test_cp_04_two_callers import drive, tool_call

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-07-client-360-coverage-graph"
SERVER = EXAMPLE / "server"

REQUIRED_ENV = (
    "CCF_CP_07_FLUREE_URL",
    "CCF_CP_07_FLUREE_LEDGER",
    "CCF_CP_07_POSTGRES_DSN",
    "CCF_CP_07_POSTGRES_SCHEMA",
)

pytestmark = pytest.mark.skipif(
    any(not os.environ.get(name) for name in REQUIRED_ENV),
    reason=(
        "cp-07's MCP door assembles from the live estate; set "
        + ", ".join(REQUIRED_ENV)
        + " to run it"
    ),
)

#: Read from `run.py` rather than restated, so the door and the in-process path
#: are demonstrated against the same client.
def _anchor(name: str) -> str:
    import ast  # noqa: PLC0415

    for node in ast.walk(ast.parse((EXAMPLE / "run.py").read_text(encoding="utf-8"))):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return str(ast.literal_eval(node.value))
    raise AssertionError(f"run.py declares no {name}")


def _load(name: str) -> Any:
    """Import one of cp-07's modules, with the example's own two roots first."""
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


def _arguments(*, lei: str, asked_at: datetime, **overrides: Any) -> dict[str, Any]:
    """cp-07's question, as the product tool's arguments.

    An override the caller does not pass is ABSENT from `parameters`, not
    present-and-defaulted — which is what makes the class default the only
    authority for it.
    """
    dep = _load("deployment")
    config = dep.config()
    schema_name = config["product_class"]["schema_name"]
    version = str(config["product_class"]["schema_version"])

    parameters: dict[str, Any] = {dep.LEI: lei, dep.PRINCIPAL_SCOPE: [lei]}
    if overrides.pop("_empty", False):
        parameters = {}
    parameters.update(overrides)

    wire = WireRequest(
        product_id=schema_name, parameters=parameters, temporal_boundary=asked_at
    )
    return {
        "tenant": config["tenant_id"],
        "product_class": schema_name,
        "version": version,
        "request": canonical_bytes(wire).decode("utf-8"),
        "subject": lei,
        "intent": "meeting-prep",
        "freshness": "standard",
        "asked_at": asked_at.isoformat(),
        "parameters": parameters,
    }


@pytest.fixture(scope="module")
def outcomes() -> dict[str, Any]:
    """Every branch, over ONE door, in ONE lifespan."""
    serve = _load("serve")
    instant = datetime.now(UTC)
    anchor, control = _anchor("DEMONSTRATION_LEI"), _anchor("CONTROL_LEI")
    with tempfile.TemporaryDirectory(prefix="cp07-door-") as scratch:
        with serve.door(root=pathlib.Path(scratch)) as opened:
            return drive(
                opened,
                {
                    # NO `limit` — the class default is the only authority.
                    "default": tool_call(_arguments(lei=anchor, asked_at=instant)),
                    "control": tool_call(_arguments(lei=control, asked_at=instant)),
                    "tight": tool_call(
                        _arguments(lei=anchor, asked_at=instant, limit=20)),
                    # A question with NO anchor — and the encoded request and
                    # the `parameters` argument agree that it has none, because
                    # a call whose two halves disagree is refused as malformed
                    # before any governance runs (C-01) and would measure the
                    # wire rather than the door.
                    "no_anchor": tool_call(
                        _arguments(lei=anchor, asked_at=instant, _empty=True)),
                },
            )


def _payload(outcomes: dict[str, Any], key: str) -> dict[str, Any]:
    is_error, text = outcomes[key]
    assert not is_error, text
    body = json.loads(text)
    assert body["content_address"], f"{key} crossed MCP with no content address"
    assert body["replay_ref"], f"{key} crossed MCP with no replay reference"
    return json.loads(body["product_json"])["payload"]


def test_the_evidence_boundary_crosses_the_wire_intact(outcomes: Any) -> None:
    """The thing rung 7 is about, asserted from OUTSIDE the process.

    A door that dropped `evidence_boundary` would hand an MCP consumer a payload
    that reads as complete — the exact failure the in-process gate exists to
    prevent, reintroduced at the transport.
    """
    boundary = _payload(outcomes, "default")["evidence_boundary"]
    admissible = (boundary["interactions_available"]
                  - boundary["withheld_need_to_know"])
    assert boundary["interactions_admitted"] < admissible
    assert boundary["truncated"] is True
    assert boundary["note"]


def test_the_class_default_resolves_for_a_caller_who_sent_no_bound(
    outcomes: Any
) -> None:
    """The door restates no default, so the Control Plane's is what applies.

    Asserted against the declaration rather than a literal: the number lives in
    `ccf_config.yaml` and this reads it from there, so moving the default moves
    both sides at once and a door that had quietly hard-coded one would go red.
    """
    dep = _load("deployment")
    declared = dep.config()["request_contract"]["defaults"]
    payload = _payload(outcomes, "default")
    assert payload["window"]["limit"] == declared["limit"]
    assert payload["window"]["since"] == declared["since"]
    assert payload["evidence_boundary"]["interactions_admitted"] == declared["limit"]


def test_the_untruncated_control_crosses_as_untruncated(outcomes: Any) -> None:
    """Without it, `truncated: True` over the wire could be a constant."""
    boundary = _payload(outcomes, "control")["evidence_boundary"]
    assert boundary["truncated"] is False
    assert boundary["interactions_admitted"] == (
        boundary["interactions_available"] - boundary["withheld_need_to_know"])


def test_a_caller_supplied_bound_reaches_the_read_over_mcp(outcomes: Any) -> None:
    """`limit` is applied IN the query, and the wire must not undo that.

    The tight call admits its own bound and — the point of the rung — reports
    more coverage gaps than the default did, from strictly less evidence.
    """
    tight = _payload(outcomes, "tight")
    default = _payload(outcomes, "default")
    assert tight["evidence_boundary"]["interactions_admitted"] == 20
    assert (tight["findings"]["coverage_gaps"]
            > default["findings"]["coverage_gaps"])


def test_a_question_with_no_anchor_is_refused_by_GOVERNANCE(outcomes: Any) -> None:
    """A question missing a required argument, and the door refuses none of it.

    `lei` and `principal_scope` are `required` in the request contract, so the
    Control Plane is what says no — with a kind from the SDK's own vocabulary,
    the declared and presented key sets, and a replay reference. The door adds
    nothing, which is the whole claim: an earlier revision hand-rolled this
    refusal, could not construct a valid `RefusalEnvelope`, and turned a
    governed "no" into an `ccf-runtime-failure` at the transport — the shape a
    producer that never booted has (`FINDINGS.md`, `CP07-F-09`).

    The kind is asserted, not merely its presence: a refusal whose kind
    flattened would be a perfectly well-formed envelope carrying the wrong
    answer, which is the failure hardest to notice.
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
    assert "lei" in declared and "lei" not in presented
    assert body["replay_ref"], (
        "the refused branch crossed MCP with no replay reference; a door that"
        " cannot record a refusal is not a governed door (`D-IMPL-256`)"
    )


def test_the_door_reimplements_no_governance() -> None:
    """Measured off the shipped file rather than asserted in prose.

    The names below are the governed path: if any of them appears in the door,
    the door has become a second governance authority and the deployment now has
    two answers to the same question.
    """
    source = (SERVER / "serve.py").read_text(encoding="utf-8")
    for forbidden in ("run_gates", "build_replay_record", "ProjectionEngine",
                      "assess_debt", "build_governed_resolver"):
        assert forbidden not in source, (
            f"server/serve.py names {forbidden!r}; the door must translate and"
            " delegate, never re-decide"
        )
    assert "produce.assemble_and_serve" in source
