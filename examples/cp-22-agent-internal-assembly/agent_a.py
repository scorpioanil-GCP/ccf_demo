"""Agent A — an ordinary agent that asks a peer a question over A2A.

**THIS FILE CONTAINS NO CCF.** No import, no type, no vocabulary, no
credential, no concept. That is not restraint, it is the claim: Agent A is a
normal A2A client, and the agent it is talking to happens to be built on a
governed context fabric it will never learn about.

Read it as the control for the whole rung. If anything CCF-shaped were
required to ask this question or to read this answer, it would have to appear
here — and `AIA-G02` asserts that it does not.

[ADAPT] nothing. This is what an adopter's counterparty already has.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import Message, Part, Role, SendMessageRequest

#: The protocol binding to speak. An A2A value; nothing to do with the peer's
#: internals.
BINDING = "JSONRPC"


async def ask(*, base_url: str, subject: str, instant: str,
              extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Ask the peer one question and return what came back.

    `extra` exists for the negative control (`AIA-G08`): a caller may put
    anything it likes on the wire, including fields named exactly like the
    peer's internal request parameters, and the answer must not change.
    """
    question: dict[str, Any] = {"subject": subject, "instant": instant}
    question.update(extra or {})
    async with httpx.AsyncClient(timeout=180.0) as http:
        card = await A2ACardResolver(httpx_client=http, base_url=base_url).get_agent_card()
        client = ClientFactory(ClientConfig(
            httpx_client=http, streaming=False,
            supported_protocol_bindings=[BINDING])).create(card)
        try:
            responses = [
                response async for response in client.send_message(
                    SendMessageRequest(message=Message(
                        message_id="headroom-question", role=Role.ROLE_USER,
                        parts=[Part(text=json.dumps(question, sort_keys=True))])))
            ]
        finally:
            await client.close()

    for response in responses:
        if response.WhichOneof("payload") != "message":
            continue
        text = "".join(part.text for part in response.message.parts if part.text)
        if text:
            return json.loads(text)
    raise RuntimeError("the peer returned no answer")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Ask a peer agent about headroom.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8722")
    parser.add_argument("--subject", required=True, help="the counterparty identifier")
    parser.add_argument("--instant", required=True, help="ISO 8601, UTC offset required")
    parser.add_argument("--noise", action="store_true",
                        help="send extra fields the peer must ignore (AIA-G08)")
    arguments = parser.parse_args(argv)

    extra = {
        "debt_tolerance": 0.01, "role": "examiner", "principal_id": "PRIN-EX-003",
        "regime": "reg-o", "connection_basis": "control", "tenant_id": "somebody-else",
    } if arguments.noise else None

    try:
        answer = asyncio.run(ask(base_url=arguments.base_url, subject=arguments.subject,
                                 instant=arguments.instant, extra=extra))
    except Exception as failure:  # noqa: BLE001 — a peer failure is an ordinary outcome
        print(f"the peer could not answer: {failure}")
        return 1

    print(f"\n   {answer['answer']}")
    print(f"\n   counterparty   {answer['counterparty']}")
    print(f"   headroom       {answer['headroom_usd']}")
    print(f"   as of          {answer['as_of']}")
    print("\n   (and nothing else — see README.md for what stayed inside the peer)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
