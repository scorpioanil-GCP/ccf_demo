"""The three live harness legs — real loops, a real model (plan 08-11, D-03/D-04).

The live counterpart of ``legs/deterministic.py``: the SAME agent, the same
adapters, the same four seams — but the seam-4 execution now reaches a live
model through each harness's own model seam, for either of two providers:

* **Ollama** (keyless local default, D-03) — resolved from
  ``CCF_OLLAMA_BASE_URL`` / ``CCF_OLLAMA_MODEL`` over the defaults in
  ``artifacts/live.yaml``.
* **Anthropic** (key-gated, D-03) — refuses with a clear message when
  ``ANTHROPIC_API_KEY`` is absent; the key is read from the environment,
  never stored, never logged (T-08-26).

How each harness's model seam is bound (RESEARCH assumption A1, resolved at
execution time against the installed SDKs):

* **Claude Agent SDK — outcome (A), native endpoint.** The pinned SDK
  (0.2.128) spawns the real CLI, and the CLI honours ``ANTHROPIC_BASE_URL``
  via ``ClaudeAgentOptions.env`` (merged over the process environment by the
  SDK's own subprocess transport). Ollama ≥0.30 serves an
  Anthropic-compatible ``/v1/messages``, verified empirically before this
  module was written — so the Ollama leg is a **real ClaudeSDKClient session
  on the native model path**, no seam substitution. The Anthropic leg is the
  same session with the process environment's key.
* **Google ADK — its own model-binding surface at 2.5.0.** A ``BaseLlm``
  subclass wrapping the provider client is registered on ADK's
  ``LLMRegistry`` for exactly the configured model name; the adapter's real
  ``LlmAgent`` (instruction provider, tools, before-tool gate — the seam-1
  carrier) is then driven by a real ``Runner``, and ADK's own event
  machinery carries the provider-reported model and token counts out
  (verified: ``Event.model_version`` / ``Event.usage_metadata`` surface from
  a custom ``BaseLlm``).
* **LangGraph — injected model callable.** LangGraph has no loop of its own
  to hook (06-13); the model seam is a callable the deployment injects. The
  callable consumes exactly the carrier's injected state (instructions +
  product bytes — seam 1's own delivery), and the provider-reported values
  travel through the adapter's real compiled graph on LangChain's own
  tracing keys, read back only out of the run's final state.

Every leg drives all four adapter seams and asserts they executed —
context injection (the product recovered out of the carrier), skill
exposure (set-equal to the bound skill-set), effect capture (a typed
governed emission), and replay hooks (a structurally complete
``HarnessTrace``). Equivalence across live legs is **structural, never
byte-equal** (D-04): live model output varies by construction, so the
assertions live on what CCF governs, not on what the model said.

Runner safeguards: every provider call carries the per-call timeout from
``CCF_LIVE_TIMEOUT_SECONDS`` / ``artifacts/live.yaml``, and the whole run is
bounded by :class:`LiveBudget` — a breached budget is a diagnostic exit 2,
never a hang. No endpoint, model, key, or timeout number is a code constant
(No-Hardcoding Rule, CLAUDE.md §6.4).
"""

from __future__ import annotations

import asyncio
import dataclasses
import os
import re
import time
from collections.abc import AsyncGenerator, Callable, Mapping
from typing import Any, ClassVar, NamedTuple

import httpx
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.models.registry import LLMRegistry
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as adk_types

from ccf.agents.agent import Agent, EmittedEffect
from ccf.contracts.canonical import content_hash
from ccf.llm import LLMClientProtocol
from ccf.products.contract import ContextProductContract
from ccf.replay.record import NO_HARNESS, HarnessTrace
from ccf_runtime.adapters.adk import AdkAdapter, AdkCarrier
from ccf_runtime.adapters.claude_agent import ClaudeAgentAdapter
from ccf_runtime.adapters.langgraph import (
    MODEL_METADATA_KEY,
    USAGE_METADATA_KEY,
    LangGraphAdapter,
)

from .deterministic import HarnessLeg, LegRun, recovered_products
from .ollama_client import LiveChatResult, ollama_client_from_config

__all__ = [
    "ANTHROPIC_API_KEY_ENV",
    "LIVE_TIMEOUT_ENV",
    "AnthropicMessagesClient",
    "LiveBudget",
    "LiveBudgetExceeded",
    "ProviderBinding",
    "ProviderUnavailable",
    "build_live_legs",
    "drive_live_leg",
    "resolve_provider",
    "resolve_timeout",
]

#: The one environment variable the Anthropic provider is gated on (D-03).
#: An interface name; the value never appears anywhere in this tree.
ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"

#: Environment variable overriding the artifact's per-call timeout default.
LIVE_TIMEOUT_ENV = "CCF_LIVE_TIMEOUT_SECONDS"


class LiveBudgetExceeded(RuntimeError):
    """The overall live-run budget elapsed; the runner exits 2 with this."""


class ProviderUnavailable(RuntimeError):
    """The selected provider cannot be used — unreachable, or its key absent."""


class LiveBudget:
    """Wall-clock bound over the whole live run (review consensus concern 2).

    Constructed once from ``runner.budget_seconds`` in
    ``artifacts/live.yaml``; every leg asks for the remaining allowance
    before (and while) it runs, and an exhausted budget raises rather than
    letting a slow provider hang the runner.
    """

    def __init__(self, *, seconds: float) -> None:
        self._seconds = seconds
        self._deadline = time.monotonic() + seconds

    def remaining(self) -> float:
        left = self._deadline - time.monotonic()
        if left <= 0:
            raise LiveBudgetExceeded(
                f"live-run budget of {self._seconds:.0f}s exhausted; raise"
                " runner.budget_seconds in artifacts/live.yaml or point the"
                " provider at a faster model"
            )
        return left


def resolve_timeout(runner: Mapping[str, Any]) -> float:
    """Per-call provider timeout: environment over the artifact default."""
    return float(
        os.environ.get(LIVE_TIMEOUT_ENV, runner["default_timeout_seconds"])
    )


class AnthropicMessagesClient:
    """Thin httpx client for Anthropic's ``POST /v1/messages`` (key-gated).

    Structurally satisfies :class:`ccf.llm.LLMClientProtocol` on the same
    terms as the Ollama client. Uses the REST surface directly over the
    already-pinned httpx — no ``anthropic`` package import anywhere under
    ``examples/`` (CINV-02 discipline), and zero new dependencies. The key
    arrives injected, sourced from the environment by
    :func:`resolve_provider`; it is sent as a header and never logged.
    """

    def __init__(
        self,
        *,
        base_url: str,
        version_header: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_tokens: int,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._version_header = version_header
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_tokens = max_tokens

    @property
    def model_version(self) -> str:
        """The configured model identifier (LLMClientProtocol)."""
        return self._model

    def chat(self, *, system: str, user: str) -> LiveChatResult:
        """One non-streaming message turn; raises ``httpx.HTTPError`` on failure."""
        response = httpx.post(
            f"{self._base_url}/v1/messages",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": self._version_header,
            },
            json={
                "model": self._model,
                "max_tokens": self._max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        document: Mapping[str, Any] = response.json()
        usage: Mapping[str, Any] = document.get("usage") or {}
        return LiveChatResult(
            text="".join(
                str(block.get("text") or "")
                for block in document.get("content") or []
                if block.get("type") == "text"
            ),
            reported_model=str(document.get("model") or self._model),
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
        )


class ProviderBinding(NamedTuple):
    """One provider, resolved: the client, the model, and the CLI's env."""

    provider_id: str
    model: str
    client: Any
    claude_env: Mapping[str, str]


def resolve_provider(
    name: str, *, live: Mapping[str, Any], runner: Mapping[str, Any]
) -> ProviderBinding:
    """Bind the selected provider from artifact config + environment.

    Raises :class:`ProviderUnavailable` for the Anthropic provider when
    ``ANTHROPIC_API_KEY`` is absent — a refusal with instructions, never a
    silent fallback (D-03, T-08-26).
    """
    timeout_seconds = resolve_timeout(runner)
    max_tokens = int(runner["max_tokens"])
    providers: Mapping[str, Any] = live["providers"]
    if name == "ollama":
        client = ollama_client_from_config(
            provider=providers["ollama"],
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
        )
        # LLMClientProtocol smoke assertion — the plan's structural check.
        assert isinstance(client, LLMClientProtocol), type(client).__name__
        # Fail fast on an unreachable endpoint (runner safeguard): the
        # per-call timeout bounds the probe, and the failure surfaces as a
        # diagnostic exit 2 before any harness leg starts.
        client.probe(timeout_seconds=min(timeout_seconds, 10.0))
        return ProviderBinding(
            provider_id="ollama",
            model=client.model_version,
            client=client,
            # The CLI needs an auth source set to take the API-key path;
            # Ollama ignores the token's value (keyless local access, D-03).
            claude_env={
                "ANTHROPIC_BASE_URL": client.base_url,
                "ANTHROPIC_API_KEY": str(providers["ollama"]["auth_token"]),
                "ANTHROPIC_MODEL": client.model_version,
                "ANTHROPIC_SMALL_FAST_MODEL": client.model_version,
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            },
        )
    if name == "anthropic":
        api_key = os.environ.get(ANTHROPIC_API_KEY_ENV, "")
        if not api_key:
            raise ProviderUnavailable(
                f"--provider anthropic requires {ANTHROPIC_API_KEY_ENV} in the"
                " environment; export it (the key is read from env only,"
                " never stored) or use --provider ollama for keyless local"
                " access"
            )
        anthropic_cfg: Mapping[str, Any] = providers["anthropic"]
        client = AnthropicMessagesClient(
            base_url=str(anthropic_cfg["base_url"]),
            version_header=str(anthropic_cfg["version_header"]),
            api_key=api_key,
            model=str(anthropic_cfg["model"]),
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
        )
        assert isinstance(client, LLMClientProtocol), type(client).__name__
        return ProviderBinding(
            provider_id="anthropic",
            model=client.model_version,
            client=client,
            # The real ClaudeSDKClient session inherits the process
            # environment (and with it the key); nothing is re-exported here.
            claude_env={"CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"},
        )
    raise ProviderUnavailable(f"unknown live provider {name!r}")


# --- the Claude leg: outcome (A), native endpoint ----------------------------


def _claude_live_execution(
    *,
    provider: ProviderBinding,
    runner: Mapping[str, Any],
    budget: LiveBudget,
) -> Callable[[object], object]:
    """A real ``ClaudeSDKClient`` session on the native model path.

    No custom transport: the SDK spawns the real CLI, which reaches the
    provider directly — Anthropic natively, Ollama via its
    Anthropic-compatible ``/v1/messages`` through ``ANTHROPIC_BASE_URL`` in
    ``ClaudeAgentOptions.env`` (outcome A of the plan's decision table).
    The session runs under the adapter's own seam-1 carrier, bounded by
    ``max_turns`` and the overall live budget.
    """

    def execute(carrier: object) -> object:
        assert isinstance(carrier, ClaudeAgentOptions), type(carrier).__name__
        options = dataclasses.replace(
            carrier,
            env={**carrier.env, **provider.claude_env},
            max_turns=int(runner["max_turns"]),
        )

        async def session() -> ResultMessage:
            client = ClaudeSDKClient(options=options)
            await client.connect()
            try:
                await client.query(str(runner["drive_turn"]))
                async for message in client.receive_response():
                    if isinstance(message, ResultMessage):
                        return message
            finally:
                await client.disconnect()
            raise AssertionError(
                "the live session ended without the SDK constructing a"
                " ResultMessage"
            )

        async def bounded() -> ResultMessage:
            return await asyncio.wait_for(session(), timeout=budget.remaining())

        return asyncio.run(bounded())

    return execute


# --- the ADK leg: LLMRegistry model binding at 2.5.0 -------------------------


def _request_text(llm_request: LlmRequest) -> tuple[str, str]:
    """Flatten ADK's request into (system, user) text for the provider."""
    system = ""
    if llm_request.config is not None:
        instruction = llm_request.config.system_instruction
        if isinstance(instruction, str):
            system = instruction
        elif instruction is not None:
            system = "\n".join(
                str(part.text)
                for part in getattr(instruction, "parts", None) or []
                if getattr(part, "text", None)
            )
    turns = [
        str(part.text)
        for content in llm_request.contents or []
        for part in content.parts or []
        if part.text
    ]
    return system, "\n".join(turns)


def _register_live_model(client: Any, model_name: str) -> None:
    """Bind the provider client on ADK's own model-binding surface.

    ``LLMRegistry.register`` + ``supported_models`` is ADK 2.5.0's sanctioned
    way to make ``LlmAgent(model=<name>)`` resolve to a custom ``BaseLlm`` —
    the adapter's carrier is untouched, and the model name that selects this
    binding is the provider's configured value, never a constant.
    """

    class _CcfLiveLlm(BaseLlm):
        _ccf_client: ClassVar[Any] = client

        @classmethod
        def supported_models(cls) -> list[str]:
            return [re.escape(model_name)]

        async def generate_content_async(
            self, llm_request: LlmRequest, stream: bool = False
        ) -> AsyncGenerator[LlmResponse, None]:
            system, user = _request_text(llm_request)
            result: LiveChatResult = await asyncio.to_thread(
                self._ccf_client.chat, system=system, user=user
            )
            yield LlmResponse(
                content=adk_types.Content(
                    role="model", parts=[adk_types.Part(text=result.text)]
                ),
                usage_metadata=adk_types.GenerateContentResponseUsageMetadata(
                    prompt_token_count=result.input_tokens,
                    candidates_token_count=result.output_tokens,
                    total_token_count=result.input_tokens + result.output_tokens,
                ),
                model_version=result.reported_model,
            )

    LLMRegistry.register(_CcfLiveLlm)
    # The registry's resolve() is lru-cached; a stale entry for this model
    # name from an earlier registration must not shadow this one.
    LLMRegistry.resolve.cache_clear()


def _adk_live_execution(
    *,
    values: Mapping[str, Any],
    provider: ProviderBinding,
    runner: Mapping[str, Any],
    budget: LiveBudget,
) -> Callable[[object], object]:
    """A real ADK ``Runner`` run of the adapter's ``LlmAgent`` with a live model.

    The model run's events carry ADK's own reported model and token counts
    (``Event.model_version`` / ``Event.usage_metadata``, populated from the
    registered ``BaseLlm``'s response); the adapter-owned capture vehicle
    then runs in the same session so seam 4 also receives the session
    identity ADK's machinery carried — exactly the two sources
    ``AdkAdapter.replay_trace`` reads, in its declared precedence.
    """

    def execute(carrier: object) -> object:
        assert isinstance(carrier, AdkCarrier), type(carrier).__name__
        _register_live_model(provider.client, provider.model)

        async def run() -> tuple[object, ...]:
            sessions = InMemorySessionService()
            await sessions.create_session(
                app_name=str(values["app_name"]),
                user_id=str(values["user_id"]),
                session_id=str(values["session_id"]),
                state=dict(carrier.session_state),
            )
            events: list[object] = []
            for vehicle, turn in (
                (carrier.llm_agent, str(runner["drive_turn"])),
                (carrier.runnable, ""),
            ):
                driver = Runner(
                    agent=vehicle,
                    app_name=str(values["app_name"]),
                    session_service=sessions,
                )
                events.extend(
                    [
                        event
                        async for event in driver.run_async(
                            user_id=str(values["user_id"]),
                            session_id=str(values["session_id"]),
                            new_message=adk_types.Content(
                                role="user", parts=[adk_types.Part(text=turn)]
                            ),
                        )
                    ]
                )
            return tuple(events)

        async def bounded() -> tuple[object, ...]:
            return await asyncio.wait_for(run(), timeout=budget.remaining())

        return asyncio.run(bounded())

    return execute


# --- the LangGraph leg: injected model callable ------------------------------


def _langgraph_live_execution(
    *,
    provider: ProviderBinding,
    runner: Mapping[str, Any],
    budget: LiveBudget,
) -> Callable[[object], object]:
    """The deployment-injected model callable at LangGraph's model seam.

    LangGraph owns no loop (06-13), so its model seam is a callable the
    deployment injects. The callable consumes exactly what seam 1 delivered
    — the carrier state's rendered instructions and product bytes — and the
    provider-reported model and token counts travel through the adapter's
    real compiled graph on LangChain's own tracing keys, read back by seam 4
    only out of the run's final state.
    """

    def execute(carrier: object) -> object:
        budget.remaining()
        state: Mapping[str, Any] = carrier.state  # type: ignore[attr-defined]
        result: LiveChatResult = provider.client.chat(
            system="\n".join((*state["instructions"], *state["products"])),
            user=str(runner["drive_turn"]),
        )
        config = dict(carrier.config)  # type: ignore[attr-defined]
        config["metadata"] = {
            **config["metadata"],
            MODEL_METADATA_KEY: result.reported_model,
            USAGE_METADATA_KEY: {
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            },
        }
        final: object = carrier.graph.invoke(  # type: ignore[attr-defined]
            carrier.state,  # type: ignore[attr-defined]
            config,
        )
        return final

    return execute


# --- the legs ----------------------------------------------------------------


def build_live_legs(
    *,
    harnesses: Mapping[str, Mapping[str, Any]],
    provider: ProviderBinding,
    runner: Mapping[str, Any],
    budget: LiveBudget,
) -> tuple[HarnessLeg, ...]:
    """All three D-IMPL-24 legs, bound to the selected live provider.

    Same adapters, same deployment vocabulary (``artifacts/harnesses.yaml``)
    as the deterministic drive — only the model binding changes: every
    adapter is constructed with the provider's model so all three legs run
    the SAME live model through their own native seams.
    """
    claude = dict(harnesses["claude-agent"])
    adk = dict(harnesses["adk"])
    langgraph = dict(harnesses["langgraph"])
    claude_adapter = ClaudeAgentAdapter(
        model=provider.model,
        mcp_server_name=str(claude["mcp_server_name"]),
        mcp_server_version=str(claude["mcp_server_version"]),
        effects="governed",
    )
    adk_adapter = AdkAdapter(
        model=provider.model,
        agent_name=str(adk["agent_name"]),
        session_id=str(adk["session_id"]),
        effects="governed",
    )
    langgraph_adapter = LangGraphAdapter(
        model=provider.model,
        thread_id=str(langgraph["thread_id"]),
        run_tags=tuple(langgraph["run_tags"]),
        effects="governed",
    )
    return (
        HarnessLeg(
            harness_id=claude_adapter.capabilities().harness_id,
            adapter=claude_adapter,
            execute=_claude_live_execution(
                provider=provider, runner=runner, budget=budget
            ),
            reported_model=provider.model,
            trace_id=str(claude["session_id"]),
        ),
        HarnessLeg(
            harness_id=adk_adapter.capabilities().harness_id,
            adapter=adk_adapter,
            execute=_adk_live_execution(
                values=adk, provider=provider, runner=runner, budget=budget
            ),
            reported_model=provider.model,
            trace_id=str(adk["session_id"]),
        ),
        HarnessLeg(
            harness_id=langgraph_adapter.capabilities().harness_id,
            adapter=langgraph_adapter,
            execute=_langgraph_live_execution(
                provider=provider, runner=runner, budget=budget
            ),
            reported_model=provider.model,
            trace_id=str(langgraph["thread_id"]),
        ),
    )


def drive_live_leg(
    leg: HarnessLeg,
    *,
    agent: Agent,
    product: ContextProductContract,
    instructions: tuple[str, ...],
    build_record: Callable[[ContextProductContract, HarnessTrace], Any],
) -> LegRun:
    """One harness's live pass through all four seams, judged structurally.

    Mirrors ``drive_leg`` but with D-04's equivalence strength: a live model
    reports its own session and token accounting, so the trace assertions
    are structural — populated, positive, this harness's own — never
    byte-equal to another leg's. The mandatory seam-conformance assertion
    (all four seams execute under a live leg) lives here.
    """
    # Seam 1 — the product recovered out of this harness's own carrier.
    carrier = leg.adapter.inject_context(
        agent=agent, products=(product,), instructions=instructions
    )
    delivered = recovered_products(carrier)
    assert len(delivered) == 1, (
        f"{leg.harness_id} delivered {len(delivered)} recoverable Context"
        " Product documents to its context surface, not exactly one"
    )
    recovered = ContextProductContract.model_validate_json(delivered[0])

    # Seam 2 — exposure is exactly the currently-bound skill-set.
    exposed = leg.adapter.expose_skills(agent=agent)
    assert set(exposed) == set(agent.bound_skill_names), (
        f"{leg.harness_id} exposed {exposed!r}, not the bound skill-set"
    )

    # Seam 3 — the governed emission, as this adapter produced it.
    emitted = leg.adapter.capture_effect(agent=agent, output=dict(product.payload))
    assert isinstance(emitted, EmittedEffect), emitted

    # Seam 4 — a structurally complete trace from a real live execution.
    trace = leg.adapter.replay_trace(execution=leg.execute(carrier))
    assert isinstance(trace, HarnessTrace)
    assert trace.harness_id == leg.harness_id != NO_HARNESS
    assert trace.model_version != NO_HARNESS, (
        f"{leg.harness_id} reported no model for a live run"
    )
    assert trace.trace_id != NO_HARNESS, (
        f"{leg.harness_id} reported no trace id for a live run"
    )
    assert trace.input_tokens > 0 and trace.output_tokens > 0, (
        f"{leg.harness_id} reported no token accounting for a live run"
    )

    record = build_record(recovered, trace)
    return LegRun(
        harness_id=leg.harness_id,
        product_bytes=delivered[0],
        record=record,
        emission_address=content_hash(emitted),
        trace=trace,
    )
