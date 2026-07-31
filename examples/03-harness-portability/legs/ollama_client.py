"""Thin httpx client for Ollama's ``POST /api/chat`` (plan 08-11, D-03).

The live legs' keyless default provider. Deliberately minimal: httpx is
already a pinned project dependency, so this module adds **zero new
packages** (the phase package gate) — no ``ollama``, no ``litellm``, no
LangChain provider package. It satisfies
:class:`ccf.llm.LLMClientProtocol` structurally (the ``model_version``
property), which is the seam the fabric names for semantic-stage model
access (CLAUDE.md §11, D-IMPL-09); ``legs/live.py`` smoke-asserts the
conformance before any leg runs.

No endpoint, model name, or credential appears as a literal here: the base
URL comes from ``CCF_OLLAMA_BASE_URL`` (default read from
``artifacts/live.yaml``), the model from ``CCF_OLLAMA_MODEL`` (same
default path), and Ollama's local API is keyless by design — nothing
resembling a key is sent (No-Hardcoding Rule, CLAUDE.md §6.4; T-08-26).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, NamedTuple

import httpx

__all__ = [
    "OLLAMA_BASE_URL_ENV",
    "OLLAMA_MODEL_ENV",
    "LiveChatResult",
    "OllamaChatClient",
    "ollama_client_from_config",
]

#: Environment variable overriding the artifact's default base URL. An
#: interface name, not a value — the value lives in the environment or in
#: ``artifacts/live.yaml``.
OLLAMA_BASE_URL_ENV = "CCF_OLLAMA_BASE_URL"

#: Environment variable overriding the artifact's default model name.
OLLAMA_MODEL_ENV = "CCF_OLLAMA_MODEL"


class LiveChatResult(NamedTuple):
    """What one live model call reported — the provider's values, verbatim.

    ``reported_model`` and the token counts are what the provider's own
    response carried, never the configured values: the fabric records what
    it invoked and the harness/provider records what it invoked, and the
    two must stay distinguishable (T-06-62).
    """

    text: str
    reported_model: str
    input_tokens: int
    output_tokens: int


class OllamaChatClient:
    """One chat completion against Ollama's native ``POST /api/chat``.

    Structurally satisfies :class:`ccf.llm.LLMClientProtocol`. Every value
    is injected — base URL, model, per-call timeout, generation cap — so
    this class holds mechanism only.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        max_tokens: int,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_tokens = max_tokens

    @property
    def model_version(self) -> str:
        """The configured model identifier (LLMClientProtocol)."""
        return self._model

    @property
    def base_url(self) -> str:
        """The resolved endpoint — exposed so the Claude leg's native path
        (``ANTHROPIC_BASE_URL``) and this client cannot drift apart."""
        return self._base_url

    def chat(self, *, system: str, user: str) -> LiveChatResult:
        """One non-streaming chat turn; raises ``httpx.HTTPError`` on failure.

        The per-call timeout is the runner safeguard from
        ``CCF_LIVE_TIMEOUT_SECONDS`` / ``artifacts/live.yaml`` — a live leg
        never waits on a provider without a bound.
        """
        response = httpx.post(
            f"{self._base_url}/api/chat",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "options": {"num_predict": self._max_tokens},
            },
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        document: Mapping[str, Any] = response.json()
        message: Mapping[str, Any] = document.get("message") or {}
        return LiveChatResult(
            text=str(message.get("content") or ""),
            reported_model=str(document.get("model") or self._model),
            input_tokens=int(document.get("prompt_eval_count") or 0),
            output_tokens=int(document.get("eval_count") or 0),
        )


def ollama_client_from_config(
    *, provider: Mapping[str, Any], timeout_seconds: float, max_tokens: int
) -> OllamaChatClient:
    """Resolve the client from environment over artifact defaults.

    ``provider`` is the ``providers.ollama`` block of
    ``artifacts/live.yaml``; the environment variables win when set, the
    artifact's defaults stand otherwise. Nothing is defaulted in code.
    """
    return OllamaChatClient(
        base_url=os.environ.get(
            OLLAMA_BASE_URL_ENV, str(provider["default_base_url"])
        ),
        model=os.environ.get(OLLAMA_MODEL_ENV, str(provider["default_model"])),
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
    )
