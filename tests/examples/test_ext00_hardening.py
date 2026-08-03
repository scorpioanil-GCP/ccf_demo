"""Permanent hardening guards for examples/external/00-hello-context (13.3).

The Phase 13.2 cross-AI review left four warn-or-skip paths in the external
example. Phase 13.3 closed them; these tests are the permanent pins so a
future edit cannot silently reopen one:

* **D-02** — ``serve.py`` refuses to compose when an ``experience.yaml``
  ``tools.*.name`` diverges from the SDK tool constant it is bound to.
* **D-06** — ``replay_server.py`` refuses to start when any fixture lacks
  its sibling, in either direction.
* **D-07** — a mutated request body reaches a loud 500 through the full
  handler path, not merely a different fingerprint dict.
* **D-08** — the Gemini fingerprint carries the URL-path model segment.
* **D-09/D-10** — the capture proxy records only 200+JSON upstream
  responses, forwards path+query verbatim, and redacts key-bearing query
  params on persist.

Decisions: D-02/D-05/D-06/D-07/D-08/D-09/D-10/D-11 (Dave, 2026-08-02).
The example modules are not packages, so each is loaded by file path with
``importlib.util`` — the pattern established by
``test_ext00_fixture_schemas.py``.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
from typing import Any

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE_DIR = REPO_ROOT / "examples" / "external" / "00-hello-context"
FIXTURES = EXAMPLE_DIR / "fixtures"


def _load_module(name: str, path: pathlib.Path) -> Any:
    """Load an example module by file path (the example dir is no package)."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_serve() -> Any:
    return _load_module("ext00_serve_under_test", EXAMPLE_DIR / "serve.py")


def _load_experience_tools() -> Any:
    import yaml

    doc = yaml.safe_load(
        (EXAMPLE_DIR / "artifacts" / "experience.yaml").read_text(
            encoding="utf-8"
        )
    )
    return doc["tools"]


# --------------------------------------------------------------------------
# D-02 / D-05 — artifact tool names must equal the SDK constants
# --------------------------------------------------------------------------


def test_committed_experience_artifact_tool_names_pass() -> None:
    """D-02: the shipped experience.yaml names match the SDK constants."""
    serve = _load_serve()
    serve.validate_tool_names(_load_experience_tools())


def test_a_drifted_artifact_tool_name_is_refused() -> None:
    """D-02/D-05: a renamed tool fails composition, naming key + constant.

    Warn-and-continue was the 13.2 residual: a deployment could advertise a
    tool name the SDK never registers and only discover it at call time.
    """
    from ccf_runtime.mcp.experience import GET_CONTEXT_TOOL

    serve = _load_serve()
    tools = json.loads(json.dumps(_load_experience_tools()))
    tools["get_context"]["name"] = "wrong_name"

    with pytest.raises(ValueError) as excinfo:
        serve.validate_tool_names(tools)

    message = str(excinfo.value)
    assert "tools.get_context.name" in message
    assert GET_CONTEXT_TOOL in message
    assert "wrong_name" in message
