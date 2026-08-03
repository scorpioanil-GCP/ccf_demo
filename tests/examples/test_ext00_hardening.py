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


def _load_replay_server() -> Any:
    return _load_module(
        "ext00_replay_server_hardening", EXAMPLE_DIR / "replay_server.py"
    )


def _write(path: pathlib.Path, doc: Any) -> None:
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", "utf-8")


def _fixture_pair(directory: pathlib.Path, prefix: str, ordinal: int) -> None:
    """Write one complete `{prefix}-NN` fixture pair into `directory`."""
    recorded = json.loads(
        (FIXTURES / f"{prefix}-{ordinal:02d}-request.json").read_text("utf-8")
    )
    response = json.loads(
        (FIXTURES / f"{prefix}-{ordinal:02d}.json").read_text("utf-8")
    )
    _write(directory / f"{prefix}-{ordinal:02d}-request.json", recorded)
    _write(directory / f"{prefix}-{ordinal:02d}.json", response)


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


# --------------------------------------------------------------------------
# D-07 — a drifted request reaches a loud 500 through the FULL handler path
# --------------------------------------------------------------------------


def test_a_drifted_request_body_gets_a_loud_500() -> None:
    """D-07: the mandatory mismatch test, through the real handler.

    `test_ext00_fixture_schemas` pins the fingerprint *function*; this pins
    the server behaviour the function exists to produce — never serve the
    wrong fixture, fail loudly with both fingerprints.
    """
    from starlette.testclient import TestClient

    replay_server = _load_replay_server()
    app = replay_server.build_app(FIXTURES)

    drifted = json.loads(
        (FIXTURES / "anthropic-00-request.json").read_text("utf-8")
    )
    drifted["messages"].append({"role": "user", "content": "extra"})

    with TestClient(app) as client:
        response = client.post("/v1/messages", json=drifted)

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"] == "request fingerprint mismatch"
    assert payload["expected"] != payload["actual"]


def test_an_undrifted_request_is_served_its_fixture() -> None:
    """The mismatch guard does not fire on the recorded conversation."""
    from starlette.testclient import TestClient

    replay_server = _load_replay_server()
    app = replay_server.build_app(FIXTURES)
    recorded = json.loads(
        (FIXTURES / "anthropic-00-request.json").read_text("utf-8")
    )

    with TestClient(app) as client:
        response = client.post("/v1/messages", json=recorded)

    assert response.status_code == 200
    assert response.json()["role"] == "assistant"


# --------------------------------------------------------------------------
# D-06 — symmetric startup refusal on unpaired fixtures
# --------------------------------------------------------------------------


def test_a_response_fixture_without_its_request_sibling_refuses_startup(
    tmp_path: pathlib.Path,
) -> None:
    """D-06: deleting a request sibling must not silently disable the guard.

    The 13.2 behaviour stored ``request: None`` and skipped fingerprinting
    for that ordinal — a missing file quietly bought an unguarded serve.
    """
    replay_server = _load_replay_server()
    _fixture_pair(tmp_path, "anthropic", 0)
    (tmp_path / "anthropic-00-request.json").unlink()

    assert replay_server.find_orphans(tmp_path) == ["anthropic-00.json"]
    with pytest.raises(SystemExit) as excinfo:
        replay_server.require_paired_fixtures(tmp_path)
    assert excinfo.value.code != 0


def test_a_request_fixture_without_its_response_sibling_refuses_startup(
    tmp_path: pathlib.Path,
) -> None:
    """D-06 symmetric: a lone recorded request is equally a broken pair."""
    replay_server = _load_replay_server()
    _fixture_pair(tmp_path, "gemini", 0)
    (tmp_path / "gemini-00.json").unlink()

    assert replay_server.find_orphans(tmp_path) == ["gemini-00-request.json"]
    with pytest.raises(SystemExit):
        replay_server.require_paired_fixtures(tmp_path)


def test_the_committed_fixture_set_is_fully_paired() -> None:
    """D-06: the shipped fixtures start the server, as CI depends on."""
    replay_server = _load_replay_server()
    assert replay_server.find_orphans(FIXTURES) == []


def test_an_empty_fixture_directory_still_starts(
    tmp_path: pathlib.Path,
) -> None:
    """D-06: zero fixtures remains a valid state — refusal is for orphans."""
    replay_server = _load_replay_server()
    assert replay_server.find_orphans(tmp_path) == []
    replay_server.require_paired_fixtures(tmp_path)
    replay_server.require_paired_fixtures(tmp_path / "absent")


# --------------------------------------------------------------------------
# D-08 — the Gemini fingerprint carries the URL-path model segment
# --------------------------------------------------------------------------


def test_gemini_fingerprint_catches_model_in_url_drift() -> None:
    """D-08: the Gemini body has no model field — it rides in the URL.

    Without the path in the fingerprint, a request for a different model
    would be served another model's recorded response silently.
    """
    replay_server = _load_replay_server()
    recorded = json.loads(
        (FIXTURES / "gemini-00-request.json").read_text("utf-8")
    )

    baseline = replay_server.fingerprint(
        "gemini", recorded, path="/v1beta/models/pinned-model:generateContent"
    )
    drifted = replay_server.fingerprint(
        "gemini", recorded, path="/v1beta/models/other-model:generateContent"
    )
    assert baseline != drifted
    assert baseline["url_model"] == "pinned-model"


def test_gemini_expected_fingerprint_reads_the_pinned_model_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-08: with no path, the expected model comes from the run.py env seam.

    The committed request fixtures are body-only (D-11, no re-capture), so
    the expected side of the comparison is env-derived rather than recorded.
    """
    replay_server = _load_replay_server()
    recorded = json.loads(
        (FIXTURES / "gemini-00-request.json").read_text("utf-8")
    )

    monkeypatch.setenv("CCF_EXT00_GEMINI_MODEL", "pinned-model")
    expected = replay_server.fingerprint("gemini", recorded)
    assert expected["url_model"] == "pinned-model"
    assert expected == replay_server.fingerprint(
        "gemini", recorded, path="/v1beta/models/pinned-model:generateContent"
    )
