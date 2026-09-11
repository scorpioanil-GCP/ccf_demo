"""cp-05's governed product over MCP — transport, not a second governance path.

`D-IMPL-298` step 3. The question this module answers is the one cp-05 was
built to answer: **is MCP merely a transport door over the governed product, or
does the author still have to rebuild CCF semantics at the transport
boundary?**

Measured before it was driven: `server/serve.py` carries **zero** lines of
governance or replay logic. Its 204 executable lines are transport ceremony,
entitlement/perspective wiring, and translate-and-delegate. This module is the
runtime half of that claim.

**ENV-GATED, deliberately.** cp-05 assembles from a live Fluree ledger and a
live Postgres estate, and seeding a cp-05-shaped fixture estate is a harness
project rather than a test (Dave, 2026-09-09). So this skips unless the
deployment's own four variables are set, and when they are set it drives the
SHIPPED door through the SHIPPED MCP driver.

**The driver is cp-04's**, imported rather than reimplemented: one lifespan,
one credential, each operation in its own session, refusals caught and returned
so the tool surface and the resource surface stay observable together.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.products.door import WireRequest

from tests.examples.test_cp_04_two_callers import drive, tool_call

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-05-credit-exposure-rollup"
SERVER = EXAMPLE / "server"

#: The four the deployment declares. Absent any one, this module has no estate.
REQUIRED_ENV = (
    "CCF_CP_05_FLUREE_URL",
    "CCF_CP_05_FLUREE_LEDGER",
    "CCF_CP_05_POSTGRES_DSN",
    "CCF_CP_05_POSTGRES_SCHEMA",
)

#: cp-05's measured determination. Fixture figures, asserted rather than
#: recomputed: a test that recomputed them would agree with any arithmetic.
DECLARED_FAMILY = 77
DECLARED_GROSS = 10_125_000_000
DECLARED_ADJUSTED = 9_325_000_000
#: 5% is the product default; the material set at it is four (2%/5%/10% -> 4/4/3).
DECLARED_MATERIAL = 4
DECLARED_THRESHOLD = "0.05"

pytestmark = pytest.mark.skipif(
    any(not os.environ.get(name) for name in REQUIRED_ENV),
    reason=(
        "cp-05's MCP door assembles from the live estate; set "
        + ", ".join(REQUIRED_ENV)
        + " to run it"
    ),
)


def _load(name: str) -> Any:
    """Import one of cp-05's modules, with the example's own two roots first."""
    import importlib

    wanted = [str(EXAMPLE), str(SERVER)]
    if sys.path[:2] != wanted:
        for entry in wanted:
            while entry in sys.path:
                sys.path.remove(entry)
        for entry in reversed(wanted):
            sys.path.insert(0, entry)
    for module in ("deployment", "produce", "projection", "assembler", "serve"):
        sys.modules.pop(module, None)
    return importlib.import_module(name)


def _arguments(*, tolerance: str | None, materiality: str) -> dict[str, Any]:
    """cp-05's declared question, as the product tool's arguments.

    **Numbers cross as canonical decimal TEXT** (`D-IMPL-302`). `WireRequest`
    refuses a float because canonical JSON renders it as text and the echo
    would then differ from what was sent; the SDK's contract-aware decode turns
    the text into an exact `Decimal` inside `resolve_effective_request`. Sending
    `0.05` as a float here would be refused at the wire, and sending it as text
    was refused `type-mismatch` until that decode existed.
    """
    dep = _load("deployment")
    question = dep.load(dep.QUESTION)[dep.DECLARATION]
    config = dep.load(dep.CONFIG)
    schema_name = config["product_class"]["schema_name"]
    version = str(config["product_class"]["schema_version"])
    parameters = {
        name: value
        for name, value in question["parameters"].items()
        if name != "intent"
    }
    parameters["materiality"] = materiality
    if tolerance is not None:
        parameters["debt_tolerance"] = tolerance
    asked_at = datetime.fromisoformat(question["asked_at"])
    wire = WireRequest(
        product_id=schema_name, parameters=parameters, temporal_boundary=asked_at
    )
    return {
        "tenant": config["tenant_id"],
        "product_class": schema_name,
        "version": version,
        "request": canonical_bytes(wire).decode("utf-8"),
        "subject": question["subject"],
        "intent": question["parameters"]["intent"],
        "freshness": question["freshness"],
        "asked_at": asked_at.isoformat(),
        "parameters": parameters,
    }


def _decision_records(root: pathlib.Path) -> list[dict[str, Any]]:
    """Decision records under the door's own store, BY CLASS not by count.

    A raw artifact count is the wrong invariant: the served branch legitimately
    writes a query-pin beside its decision record, so counting files would read
    that as a double-mint — and would equally hide a real one. Decision records
    are the documents carrying the five replay dimensions; `policy_bindings` is
    the discriminator.
    """
    store = root / "replay" / "artifacts-store"
    found: list[dict[str, Any]] = []
    for path in sorted(store.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(document, dict) and "policy_bindings" in document:
            found.append(document)
    return found


@pytest.fixture(scope="module")
def outcomes() -> dict[str, tuple[bool, str]]:
    """Both governed branches, over ONE door, in ONE lifespan."""
    serve = _load("serve")
    with tempfile.TemporaryDirectory(prefix="cp05-door-") as scratch:
        root = pathlib.Path(scratch)
        with serve.door(root=root) as opened:
            results = drive(
                opened,
                {
                    "default": tool_call(
                        _arguments(tolerance=None, materiality=DECLARED_THRESHOLD)
                    ),
                    "tolerant": tool_call(
                        _arguments(tolerance="1.00", materiality=DECLARED_THRESHOLD)
                    ),
                    # `D-IMPL-304`, driven in the SAME lifespan so the record
                    # count below spans all three calls.
                    "malformed": tool_call(
                        _arguments(tolerance="NaN", materiality=DECLARED_THRESHOLD)
                    ),
                },
            )
        results["_records"] = _decision_records(root)  # type: ignore[assignment]
    return results


def test_the_product_default_withholds_over_mcp(outcomes: Any) -> None:
    """0.25 default against D_c 1.000 — the governed answer is WITHHELD.

    And the authority reaches the WIRE. `authority: "default"` crossing MCP is
    the whole chain visible from outside the process: product default ->
    effective request resolution -> Debt comparison -> governed withholding ->
    replay -> MCP response. A caller who never sent a tolerance is told which
    authority supplied the one that withheld their answer.
    """
    is_error, text = outcomes["default"]
    body = json.loads(text)

    assert not is_error, "a governed withholding is a successful response"
    assert body["product_json"] is None, "a withheld determination served a product"
    assert body["content_address"] is None
    refusal = body["refusal"]
    assert refusal["kind"] == "tolerance-exceeded", refusal["kind"]
    assert json.loads(refusal["fields"]["authority"]) == "default"
    assert body["replay_ref"], "the withheld branch crossed MCP with no replay reference"


def test_a_caller_tolerance_serves_the_same_determination(outcomes: Any) -> None:
    """1.00 from the caller — same Debt, same truth, different fulfillment.

    The figures are cp-05's measured determination and they are asserted here
    over the WIRE, so this says the governed product crossed MCP intact rather
    than that the door produced something plausible.

    Declared product gate `CER-G08` (`CP-SPEC-005` §G.2).
    """
    is_error, text = outcomes["tolerant"]
    body = json.loads(text)

    assert not is_error
    assert body["content_address"], "a served product crossed MCP with no address"
    assert body["replay_ref"]
    payload = json.loads(body["product_json"])["payload"]

    assert payload["family"]["nodes"] == DECLARED_FAMILY
    assert payload["measures"]["gross"]["committed"] == DECLARED_GROSS
    assert payload["measures"]["adjusted"]["committed"] == DECLARED_ADJUSTED
    assert payload["threshold"] == DECLARED_THRESHOLD
    assert len(payload["material"]) == DECLARED_MATERIAL, (
        "the 5% materiality semantics did not survive the wire; `0.05` crossed"
        " as canonical decimal text and must reach the projection as a number"
        " (D-IMPL-302)"
    )


def test_the_payload_carries_no_governance_metadata(outcomes: Any) -> None:
    """`effective_request` is the envelope's, not the business content's.

    `D-IMPL-299`: replay dimension 2 owns which authority supplied each value.
    A payload restating it would reconstruct governance state the fabric
    already holds, and would make the content address a function of how the
    answer was authorised rather than of the answer.
    """
    payload = json.loads(json.loads(outcomes["tolerant"][1])["product_json"])["payload"]

    assert "effective_request" not in payload


def test_one_decision_record_per_determination(outcomes: Any) -> None:
    """Two determinations, two decision records — counted BY CLASS.

    The served branch also writes a query-pin, so a raw artifact count is the
    wrong invariant in both directions. This counts documents carrying the
    replay dimensions, which is what "the door minted a second record" would
    actually mean.
    """
    records = outcomes["_records"]

    assert len(records) == 2, (
        f"{len(records)} decision records for 2 governed determinations — the"
        " door minted its own, or one determination went unrecorded"
    )


def test_the_wire_carried_decimal_text_not_a_float() -> None:
    """The transport invariant this product is the first to need.

    `WireRequest` refuses a float outright, so the assertion is that the
    canonical encoding still round-trips the lexical form: `"0.05"` in, `"0.05"`
    out, and the exact decimal is established inside the SDK rather than on the
    wire.
    """
    arguments = _arguments(tolerance=None, materiality=DECLARED_THRESHOLD)
    encoded = json.loads(arguments["request"])

    assert encoded["parameters"]["materiality"] == DECLARED_THRESHOLD
    assert Decimal(DECLARED_THRESHOLD) != Decimal(0.05), (
        "the fixture's own premise: 0.05 is not representable as a binary float"
    )


def test_a_malformed_number_is_judged_correctly_but_records_nothing(
    outcomes: Any,
) -> None:
    """`D-IMPL-304` — THE KNOWN CARRY, asserted rather than described.

    A malformed numeric lexical value is judged **correctly**: the resolver
    names it `type-mismatch` on `debt_tolerance`, declared `number`, presented
    `str`. What is wrong is the DELIVERY. cp-05 resolves the effective request
    once before acquisition — the walk cannot know its depth or edge flags
    until it knows what the caller effectively asked — and that pre-resolution
    raises, so `GovernedResolver`'s own refusal path, which DOES record
    resolution refusals to replay, never runs. The caller gets a runtime
    failure where a governed refusal with a replay reference belongs.

    **This is not an MCP defect and the migration did not introduce it** — the
    hand-composed spine raised in the same place. It is carried visibly rather
    than fixed by redesigning acquisition ordering inside Step 3 (Dave,
    2026-09-09).

    **The record count is the sharp end.** Three calls crossed this door and
    :func:`test_one_decision_record_per_determination` still finds exactly two
    decision records — because this determination produced none. When the carry
    is closed, that test goes red at three, which is the signal wanted: a fix
    breaks the assertion describing the defect instead of the defect quietly
    outliving its record.
    """
    is_error, text = outcomes["malformed"]

    assert is_error, (
        "the malformed value was accepted; the contract must refuse a"
        " non-canonical numeric lexical form (D-IMPL-302)"
    )
    assert "ccf-runtime-failure" in text, (
        "the malformed branch no longer surfaces as a runtime failure — if it"
        " now returns a governed refusal, D-IMPL-304 is CLOSED and this"
        " assertion, and the record count above, must move with it"
    )
    with pytest.raises(ValueError):
        json.loads(text)
