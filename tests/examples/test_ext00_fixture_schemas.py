"""Fixture schema smoke-tests for examples/external/00-hello-context (D-01b).

The committed model-API fixtures are live captures (phase 13.2 plan 03);
these tests pin their structure against the installed SDKs' own types so
a hand-edit cannot drift a fixture into a shape the real vendor API would
never produce. Response fixtures validate against the SDKs' Pydantic
models; request fixtures get structural key/shape assertions (Anthropic
request types are TypedDicts, not validatable models).

A cheap unit test also exercises replay_server's fingerprint helper (D-03)
so mismatch detection is verified without booting the server.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
from typing import Any

import pytest
from anthropic.types import Message
from google.genai.types import GenerateContentResponse

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE_DIR = REPO_ROOT / "examples" / "external" / "00-hello-context"
FIXTURES = EXAMPLE_DIR / "fixtures"


def _fixture_paths(pattern: str) -> list[pathlib.Path]:
    return sorted(FIXTURES.glob(pattern))


def _load(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _response_paths(prefix: str) -> list[pathlib.Path]:
    return [
        p
        for p in _fixture_paths(f"{prefix}-*.json")
        if not p.name.endswith("-request.json")
    ]


def test_fixture_directory_is_populated() -> None:
    """The suite must collect >= 1 test per committed fixture file."""
    assert _response_paths("anthropic"), "no anthropic response fixtures"
    assert _response_paths("gemini"), "no gemini response fixtures"


@pytest.mark.parametrize(
    "path", _response_paths("anthropic"), ids=lambda p: p.name
)
def test_anthropic_response_fixture_validates(path: pathlib.Path) -> None:
    message = Message.model_validate(_load(path))
    assert message.role == "assistant"
    assert message.content, f"{path.name}: empty content block list"


@pytest.mark.parametrize(
    "path", _response_paths("gemini"), ids=lambda p: p.name
)
def test_gemini_response_fixture_validates(path: pathlib.Path) -> None:
    # Parse through the SDK's own client path (`_from_response`), which
    # strips forward-compat extra fields before Pydantic validation —
    # exactly what the live google-genai client does with a real vendor
    # response. The live capture carries fields (e.g.
    # `usageMetadata.serviceTier`) newer than the pinned SDK's model, so
    # bare `model_validate` would reject a genuine vendor payload.
    response = GenerateContentResponse._from_response(
        response=_load(path), kwargs={}
    )
    assert response.candidates, f"{path.name}: no candidates"


@pytest.mark.parametrize(
    "path", _fixture_paths("anthropic-*-request.json"), ids=lambda p: p.name
)
def test_anthropic_request_fixture_shape(path: pathlib.Path) -> None:
    body = _load(path)
    assert isinstance(body["model"], str) and body["model"]
    assert isinstance(body["messages"], list) and body["messages"]
    assert isinstance(body["tools"], list) and body["tools"]
    for tool in body["tools"]:
        assert isinstance(tool["name"], str) and tool["name"]


@pytest.mark.parametrize(
    "path", _fixture_paths("gemini-*-request.json"), ids=lambda p: p.name
)
def test_gemini_request_fixture_shape(path: pathlib.Path) -> None:
    body = _load(path)
    assert isinstance(body["contents"], list) and body["contents"]
    declarations = body["tools"][0]["functionDeclarations"]
    assert isinstance(declarations, list) and declarations
    for declaration in declarations:
        assert isinstance(declaration["name"], str) and declaration["name"]


def _load_replay_server() -> Any:
    """Load the example's replay server by file path (not a package)."""
    spec = importlib.util.spec_from_file_location(
        "ext00_replay_server_under_test", EXAMPLE_DIR / "replay_server.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fingerprint_detects_drift() -> None:
    """D-03: a mutated request body produces a different fingerprint."""
    replay_server = _load_replay_server()
    recorded = _load(FIXTURES / "anthropic-00-request.json")
    baseline = replay_server.fingerprint("anthropic", recorded)

    drifted = json.loads(json.dumps(recorded))
    drifted["messages"].append({"role": "user", "content": "extra"})
    assert replay_server.fingerprint("anthropic", drifted) != baseline

    gemini_recorded = _load(FIXTURES / "gemini-00-request.json")
    gemini_baseline = replay_server.fingerprint("gemini", gemini_recorded)
    gemini_drifted = json.loads(json.dumps(gemini_recorded))
    gemini_drifted["tools"][0]["functionDeclarations"].pop()
    assert (
        replay_server.fingerprint("gemini", gemini_drifted)
        != gemini_baseline
    )
    # The gemini fingerprint carries no model field — it rides in the URL.
    assert "model" not in gemini_baseline
