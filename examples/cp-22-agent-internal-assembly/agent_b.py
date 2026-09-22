"""Agent B — an ordinary A2A agent that happens to be built on CCF.

THE CENTRAL INVARIANT, and every line here serves it:

    CCF TERMINATES INSIDE THIS PROCESS. A2A is an external agent protocol and
    is NOT a CCF delivery surface.

Agent B receives a narrow A2A request, maps ONLY the approved fields into its
own use-case invocation, assembles a Context Product internally, lets CCF's
governance and debt decide whether an answer may be used, deliberately
extracts a LOSSY use-case answer, and sends that answer over A2A.

**The Context Product never crosses the boundary.** Neither does its content
address, its replay reference, its Context Debt, its lineage, any CCF artifact
URI, any CCF refusal vocabulary, or any policy or grant identifier
(`artifacts/wire-contract.yaml`, `AIA-G05`).

[ADAPT] the extraction in `_answer_from` and the question in `_ask_ccf`. Those
two functions are the whole of what a different use case would change.

WHAT THIS FILE DELIBERATELY DOES NOT DO:

- it does not import `ccf_runtime.peering` (`AIA-G09`). Peering is a
  fabric-to-fabric exchange in which a Context Product really crosses and
  another Control Plane admits it. Agent A has no fabric and no Control Plane;
  it is an agent, and this is a conversation.
- it does not read a third field from the wire (`AIA-G02`, `Q3`).
- it does not let anything a caller says reach the policy envelope
  (`AIA-G08`, `Q3`).
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import uvicorn
import yaml
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, Message, Part, Role
from starlette.applications import Starlette

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent.parent
DECLARATION: Mapping[str, Any] = yaml.safe_load(
    (HERE / "artifacts" / "agent-b.yaml").read_text(encoding="utf-8"))["declaration"]
WIRE: Mapping[str, Any] = yaml.safe_load(
    (HERE / "artifacts" / "wire-contract.yaml").read_text(encoding="utf-8"))["declaration"]


class CannotAnswer(RuntimeError):
    """A governed determination did not yield a usable answer.

    THE TRANSLATION LAYER, and it is deliberately thin. The A2A harness turns
    an exception out of `execute` into a JSON-RPC error, which is this
    protocol's own non-success — so a refusal reaches Agent A as a FAILURE
    (`AIA-G07`) carrying only the use-case sentence (`AIA-G06`).

    The CCF refusal — its reason, its error code, its replay reference — is
    read, branched on, and DROPPED. It is internal governance structure and
    Agent A can do nothing with it.
    """


# =========================================================================
# THE CCF HALF — the whole of it
# =========================================================================


def _consumed_tree() -> Path:
    return REPO_ROOT / DECLARATION["consumed_product"]["tree"]


def _ask_ccf(*, subject: str, instant: str, strict: bool) -> Mapping[str, Any]:
    """Assemble the governed product IN THIS PROCESS and return its payload.

    ONLY `subject` AND `instant` COME FROM THE CALLER. Everything that governs
    — the product, the principal, the rendering, the intent, the regime, the
    connection basis, the mitigation posture and the debt tolerance — is read
    from `artifacts/agent-b.yaml` and is unreachable from the wire (`Q3`).

    Raises:
        CannotAnswer: the determination was refused or withheld. The CCF
            refusal is inspected here and does not leave this function.
    """
    sys.path.insert(0, str(_consumed_tree()))
    try:
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415
    finally:
        sys.path.remove(str(_consumed_tree()))

    from ccf.projection.plan import Perspective  # noqa: PLC0415
    from ccf.replay.serve import ServedProduct  # noqa: PLC0415

    envelope = DECLARATION["envelope"]
    principal = DECLARATION["principal"]
    # A STRING, CONVERTED TO `Decimal` HERE. Parsed from YAML as a bare number
    # this is a `float`, and `canonical_bytes` refuses a float as not
    # bit-stable — so a tolerance declared the obvious way raises during
    # request canonicalization instead of governing anything (`AIA-F-01`).
    tolerance = Decimal(str(
        DECLARATION["strict_debt_tolerance" if strict else "debt_tolerance"]))

    with tempfile.TemporaryDirectory(prefix="agent-b-") as scratch:
        with produce.product(Path(scratch)) as opened:
            asked = produce.large_exposure_question(
                opened,
                anchor=subject,
                asked_at=datetime.fromisoformat(instant),
                intent=envelope["intent"],
                freshness=envelope["freshness"],
                **{
                    deployment.AS_OF: instant,
                    deployment.REGIME: envelope["regime"],
                    deployment.CONNECTION_BASIS: envelope["connection_basis"],
                    deployment.APPLY_MITIGATION: envelope["apply_mitigation"],
                    "debt_tolerance": tolerance,
                },
            )
            outcome = opened.answer(asked, perspective=Perspective(
                principal_id=principal["principal_id"], role=principal["role"]))

            if not isinstance(outcome, ServedProduct):
                # THE REFUSAL IS READ AND DROPPED. Nothing about it travels.
                raise CannotAnswer(WIRE["non_success"]["reason_text"])

            # The replay record exists and is resolvable INSIDE Agent B
            # (`AIA-G11`). It is not returned, not logged to the wire, and not
            # referenced in the answer.
            opened.record_of(outcome)
            return dict(outcome.product.payload)


def _answer_from(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """THE LOSSY EXTRACTION. A typed governed contract becomes four plain values.

    This is the seam the rung exists to demonstrate, and losing things is what
    it is for. The product carries a member roster, a normalized capital base
    with its unit authority, an effective-dated regime with quoted rulebook
    text, every applicable limit with its counting rules, a conflict between
    two internal authorities, a disclosed freshness asymmetry, Context Debt by
    the per-factor-minimum law, a content address and a replay record.

    Agent A asked whether there is headroom. It gets whether there is headroom.
    """
    group = payload["group"]
    evaluation = payload["evaluation"]
    members = payload.get("members") or []
    anchor = next((m for m in members if m.get("is_anchor") == "true"), {})
    headroom = evaluation["binding_limit_headroom"]
    name = anchor.get("legal_name") or group["anchor_lei"]
    fits = not headroom.startswith("-")
    return {
        "answer": (
            f"{name} is {'within' if fits else 'over'} its binding exposure limit"
            f" as of {payload['as_of'][:10]}."
        ),
        "counterparty": name,
        "headroom_usd": headroom,
        "as_of": payload["as_of"],
    }


# =========================================================================
# THE A2A HALF — the harness, used as given
# =========================================================================


def _read_request(text: str) -> tuple[str, str]:
    """Take EXACTLY the two admitted fields. Everything else is IGNORED.

    Ignored rather than refused, deliberately: a caller that adds a field —
    including one named exactly like a cp-21 request parameter — changes
    nothing about the determination, and `AIA-G08` asserts the answer is
    byte-identical with and without them.
    """
    try:
        sent = json.loads(text)
    except json.JSONDecodeError as bad:
        raise CannotAnswer("the question was not understood") from bad
    if not isinstance(sent, Mapping):
        raise CannotAnswer("the question was not understood")
    admitted = WIRE["inbound_admitted_fields"]
    missing = [field for field in admitted if not sent.get(field)]
    if missing:
        raise CannotAnswer(f"the question is missing: {', '.join(missing)}")
    return str(sent[admitted[0]]), str(sent[admitted[1]])


class HeadroomExecutor(AgentExecutor):
    """Where A2A hands control to the application. Six steps, and no loop."""

    def __init__(self, *, strict: bool) -> None:
        self._strict = strict

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        message = context.message
        if message is None:
            raise CannotAnswer("the question was not understood")
        text = "".join(part.text for part in message.parts if getattr(part, "text", ""))
        subject, instant = _read_request(text)
        payload = _ask_ccf(subject=subject, instant=instant, strict=self._strict)
        answer = _answer_from(payload)
        await event_queue.enqueue_event(Message(
            message_id="headroom-answer",
            role=Role.ROLE_AGENT,
            parts=[Part(text=json.dumps(answer, sort_keys=True))],
        ))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise CannotAnswer("this agent answers within the request; there is nothing to cancel")


def agent_card(*, port: int | None = None) -> AgentCard:
    """The card, built from declared values. No literal belongs here.

    THE CARD MUST ADVERTISE THE PORT ACTUALLY BOUND. A client resolves the
    card and then dials the URL the card gives it, so a card built from the
    declared port while the server listens on another is a peer that answers
    discovery and then refuses every call. Measured: it reads exactly like an
    intermittent network fault (`AIA-F-03`).
    """
    a2a = DECLARATION["a2a"]
    root = f"http://{a2a['host']}:{port or a2a['port']}"
    return AgentCard(
        name=a2a["name"], version=a2a["version"], description=a2a["description"],
        supported_interfaces=[AgentInterface(
            protocol_binding=a2a["protocol_binding"], url=f"{root}{a2a['rpc_path']}")],
        capabilities=AgentCapabilities(),
        default_input_modes=list(a2a["input_modes"]),
        default_output_modes=list(a2a["output_modes"]),
        skills=[],
    )


def app(*, strict: bool = False, port: int | None = None) -> Starlette:
    """The A2A routes, composed from `a2a-sdk`. None of them is written here."""
    card = agent_card(port=port)
    handler = DefaultRequestHandler(
        agent_executor=HeadroomExecutor(strict=strict),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    return Starlette(routes=[
        *create_agent_card_routes(card),
        *create_jsonrpc_routes(handler, DECLARATION["a2a"]["rpc_path"]),
    ])


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Serve Agent B over A2A.")
    parser.add_argument("--port", type=int, default=DECLARATION["a2a"]["port"])
    parser.add_argument("--strict", action="store_true",
                        help="use the strict debt tolerance (AIA-G10)")
    arguments = parser.parse_args(argv)
    uvicorn.run(app(strict=arguments.strict, port=arguments.port),
                host=DECLARATION["a2a"]["host"], port=arguments.port, log_level="error")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
