"""Leg 3 — a textbook Google ADK agent over the CCF MCP front door (D-05).

Pure ADK: an ``LlmAgent`` whose only tool surface is an ``McpToolset``
pointed at the CCF experience server — ADK discovers ``get_context`` (and
the rest) from the server's own tools/list, so no tool schema is duplicated
here. Zero CCF imports (D-06); the only CCF knowledge is ``CCF_MCP_URL``
and ``CCF_TOKEN``.

Determinism in CI is transport-level only (D-09): ``GOOGLE_GEMINI_BASE_URL``
points the ``google-genai`` client at ``replay_server.py`` and
``GOOGLE_API_KEY=ci-replay`` keeps the non-Vertex API-key path; live mode
is this same file with those variables unset. No CI/live branch exists.

Environment: ``CCF_MCP_URL``, ``CCF_TOKEN``, ``CCF_EXAMPLE_GEMINI_MODEL``
(model names never appear in code), ``CCF_EXAMPLE_QUESTION`` (prompts never
appear in code — CLAUDE.md §6.4). All four are REQUIRED: a default here
would be a prompt in code that runs on the default path, which is what the
deployment declares in ``artifacts/experience.yaml`` and ``run.py`` passes.
"""

from __future__ import annotations

import asyncio
import os
import sys

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.genai import types

APP = "external-consumer"


async def main() -> None:
    url = os.environ["CCF_MCP_URL"]
    token = os.environ["CCF_TOKEN"]
    model = os.environ["CCF_EXAMPLE_GEMINI_MODEL"]
    question = os.environ["CCF_EXAMPLE_QUESTION"]

    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=url, headers={"Authorization": f"Bearer {token}"}
        )
    )
    agent = LlmAgent(model=model, name="external_consumer", tools=[toolset])
    sessions = InMemorySessionService()
    await sessions.create_session(app_name=APP, user_id=APP, session_id=APP)
    runner = Runner(agent=agent, app_name=APP, session_service=sessions)

    decision = ""
    try:
        async for event in runner.run_async(
            user_id=APP,
            session_id=APP,
            new_message=types.Content(
                role="user", parts=[types.Part(text=question)]
            ),
        ):
            if event.is_final_response() and event.content:
                decision = "".join(
                    part.text or "" for part in event.content.parts or []
                )
    finally:
        await toolset.close()

    if not decision:
        sys.exit("the model returned no final text")
    print(decision)


if __name__ == "__main__":
    asyncio.run(main())
