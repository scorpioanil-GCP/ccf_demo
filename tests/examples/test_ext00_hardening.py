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
import os
import pathlib
import shutil
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


def _load_experience_doc() -> Any:
    import yaml

    doc: Any = yaml.safe_load(
        (EXAMPLE_DIR / "artifacts" / "experience.yaml").read_text(
            encoding="utf-8"
        )
    )
    return doc


def test_the_committed_agent_exposure_declares_no_agents() -> None:
    """The shipped artifact composes: no agents, no agent tools, no seams."""
    serve = _load_serve()
    doc = _load_experience_doc()
    serve.validate_agent_exposure(doc["agent_exposure"], doc["tool_allowlist"])


def test_declaring_an_agent_without_allowlisting_the_tool_is_refused() -> None:
    """WR-05: the README's "what to change first" instinct must not defer.

    An entry added under `agent_exposure.agents` while `list_agents` stays
    off the allowlist is unreachable; with the tool on, a raw artifact
    mapping would flow untyped into the SDK's `ExposedAgent` surface and
    fail at call time. Either way the refusal belongs at the artifact
    boundary (CLAUDE.md §11).
    """
    from ccf_runtime.mcp.experience import LIST_AGENTS_TOOL

    serve = _load_serve()
    doc = _load_experience_doc()

    with pytest.raises(ValueError) as excinfo:
        serve.validate_agent_exposure(
            {"agents": [{"name": "analyst"}]}, doc["tool_allowlist"]
        )

    assert LIST_AGENTS_TOOL in str(excinfo.value)


# --------------------------------------------------------------------------
# IN-04 — the D-16 reproduction names its serve instead of taking the newest
# --------------------------------------------------------------------------


def test_run_py_selects_the_d16_serve_record_by_label_not_position() -> None:
    """IN-04: `versions[-1]` coupled PASS 8 to `_mcp_probe`'s read order.

    Both serve paths append a `ServeRequestRecord` under the same verified
    client_id, so "newest in the store" only matched the compared bytes
    because `read_resource` happens to run before `call_tool`. Reordering
    those two lines would have compared a record from a different serve —
    and passed anyway today (one product, identical bytes), which is the
    hazard. The label seam is shared: `serve.py` writes it, `run.py` reads
    by it, so a rename cannot silently split the two sides.
    """
    serve = _load_serve()
    source = (EXAMPLE_DIR / "run.py").read_text(encoding="utf-8")

    label = serve.get_context_request_label(tenant="t", entity="e")
    assert label == "get_context tenant=t entity=e"
    # run.py must not resolve "newest in the store" any more. (The phrase
    # still appears in the docstring explaining what was wrong; it is the
    # resolution call that must be gone.)
    assert "content_address=versions[-1]" not in source
    assert "fabric.get_context_request_label(" in source
    assert "serve_request_label=" in source


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


def test_a_fixture_stem_containing_json_resolves_its_real_sibling(
    tmp_path: pathlib.Path,
) -> None:
    """IN-03: `_load_fixtures` must anchor the suffix, not replace-all.

    `find_orphans` already anchors (`name[: -len('.json')]`), so a stem
    carrying `.json` earlier in the name passes the D-06 pairing check.
    `_load_fixtures` used `path.name.replace(".json", "-request.json")`,
    which substitutes EVERY occurrence — turning
    `anthropic-v1.json-00.json` into `anthropic-v1-request.json-00-request.json`
    and raising FileNotFoundError *after* the set was declared sound.

    Every committed fixture name is immune (D-11 keeps them that way), so
    this pins the latent case rather than a live break.
    """
    replay_server = _load_replay_server()
    stem = "anthropic-v1.json-00"
    source = json.loads((FIXTURES / "anthropic-00-request.json").read_text("utf-8"))
    response = json.loads((FIXTURES / "anthropic-00.json").read_text("utf-8"))
    _write(tmp_path / f"{stem}-request.json", source)
    _write(tmp_path / f"{stem}.json", response)

    # The pairing gate accepts it, which is precisely what makes the
    # downstream replace-all a latent defect rather than a caught one.
    assert replay_server.find_orphans(tmp_path) == []
    replay_server.require_paired_fixtures(tmp_path)

    loaded = replay_server._load_fixtures(tmp_path)
    assert len(loaded["anthropic"]) == 1
    assert loaded["anthropic"][0]["request"] == source
    assert loaded["anthropic"][0]["response"] == response


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


def test_gemini_expected_fingerprint_takes_the_pinned_model_explicitly() -> None:
    """D-08: with no path, the expected model is an explicit argument.

    The committed request fixtures are body-only (D-11, no re-capture), so
    the expected side of the comparison is harness-pinned rather than
    recorded. It arrives as a parameter: `fingerprint` is a pure reduction
    and reads no process environment.
    """
    replay_server = _load_replay_server()
    recorded = json.loads(
        (FIXTURES / "gemini-00-request.json").read_text("utf-8")
    )

    expected = replay_server.fingerprint(
        "gemini", recorded, expected_gemini_model="pinned-model"
    )
    assert expected["url_model"] == "pinned-model"
    assert expected == replay_server.fingerprint(
        "gemini", recorded, path="/v1beta/models/pinned-model:generateContent"
    )


def test_fingerprint_ignores_the_ambient_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WR-02: the reduction must not depend on invisible global state."""
    replay_server = _load_replay_server()
    recorded = json.loads(
        (FIXTURES / "gemini-00-request.json").read_text("utf-8")
    )

    monkeypatch.setenv(replay_server.GEMINI_MODEL_ENV, "ambient-model")
    assert replay_server.fingerprint("gemini", recorded)["url_model"] == ""


def test_an_unset_gemini_model_env_is_a_named_500_not_a_silent_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WR-02: unset must be loud and named, not fingerprinted as "".

    Standalone `python replay_server.py` leaves the variable unset. The
    old default produced a mismatch diagnostic comparing "" against a real
    model, which the operator had no way to interpret.
    """
    from starlette.testclient import TestClient

    replay_server = _load_replay_server()
    monkeypatch.delenv(replay_server.GEMINI_MODEL_ENV, raising=False)
    app = replay_server.build_app(FIXTURES)

    recorded = json.loads(
        (FIXTURES / "gemini-00-request.json").read_text("utf-8")
    )
    with TestClient(app) as client:
        response = client.post(
            "/v1beta/models/m:generateContent", json=recorded
        )

    assert response.status_code == 500
    assert replay_server.GEMINI_MODEL_ENV in response.json()["error"]


@pytest.mark.parametrize("empty", ["", None])
def test_an_empty_gemini_model_is_treated_as_unset(
    monkeypatch: pytest.MonkeyPatch, empty: str | None
) -> None:
    """NEW-01: an exported-but-empty label must take the same named 500.

    `build_app` guarded on `is None`, so `CCF_EXT00_GEMINI_MODEL=` counted
    as SET — the shape a shell produces from an unset substitution like
    `CCF_EXT00_GEMINI_MODEL="$SOME_TYPO"`. It bypassed the loud-500 path
    and forwarded an empty expected label into `fingerprint()`, yielding
    `url_model: ""` against a real model: precisely the uninterpretable
    mismatch the 500 exists to prevent. There is no intentionally-empty
    model label, so empty collapses to unset — through the argument seam
    and through the env seam alike.
    """
    from starlette.testclient import TestClient

    replay_server = _load_replay_server()
    if empty is None:
        monkeypatch.setenv(replay_server.GEMINI_MODEL_ENV, "")
        app = replay_server.build_app(FIXTURES)
    else:
        monkeypatch.delenv(replay_server.GEMINI_MODEL_ENV, raising=False)
        app = replay_server.build_app(FIXTURES, expected_gemini_model=empty)

    recorded = json.loads(
        (FIXTURES / "gemini-00-request.json").read_text("utf-8")
    )
    with TestClient(app) as client:
        response = client.post(
            "/v1beta/models/m:generateContent", json=recorded
        )

    assert response.status_code == 500
    payload = response.json()
    assert replay_server.GEMINI_MODEL_ENV in payload["error"]
    # Never the fingerprint-mismatch path: that diagnostic would compare
    # "" against a real model and tell the operator nothing actionable.
    assert payload["error"] != "request fingerprint mismatch"


def test_the_gemini_fixture_label_matches_what_the_readme_documents() -> None:
    """WR-01: nothing else ties the label in run.py to the capture recipe.

    `fixtures/README.md`'s Normalize step tells the operator which literal
    to write into the recordings; `run.py` pins the same literal for the
    replay harness. A rename in one place silently diverged from the other.
    """
    run = _load_module("ext00_run_label", EXAMPLE_DIR / "run.py")
    readme = (FIXTURES / "README.md").read_text("utf-8")
    assert f"`{run.GEMINI_FIXTURE_LABEL}`" in readme


# --------------------------------------------------------------------------
# D-09 / D-10 — capture-proxy recording gate, query forwarding, redaction
# --------------------------------------------------------------------------

#: One minimal Gemini-shaped request body. The proxy never inspects the
#: body's shape, so a placeholder is enough to exercise the gate.
_PROXY_BODY = {"contents": [{"parts": [{"text": "hello"}]}]}


#: The capture secret these tests present as the first path segment
#: (IN-01). `main()` mints a random one per process; a fixed value keeps
#: the tests readable, and `build_app` requires it either way.
_PROXY_SECRET = "test-capture-secret"


def _capture_url(path: str) -> str:
    """Prefix a vendor path with the capture secret segment (IN-01)."""
    return f"/{_PROXY_SECRET}{path}"


def _load_capture_proxy() -> Any:
    return _load_module(
        "ext00_capture_proxy_hardening", FIXTURES / "capture_proxy.py"
    )


def _proxy_client(
    out_dir: pathlib.Path,
    responder: Any,
    monkeypatch: pytest.MonkeyPatch,
    *,
    raise_server_exceptions: bool = True,
) -> Any:
    """A TestClient over the capture proxy with a mocked upstream.

    `responder` receives the forwarded `httpx.Request` and returns the
    `httpx.Response` the vendor would have. No sockets, no API keys
    (D-11).

    `raise_server_exceptions=False` makes an unhandled handler exception
    observable as a 500 response rather than being re-raised into the
    test — which is how a refusal that *crashes* is told apart from a
    refusal that *refuses* (WR-01).
    """
    import httpx
    from starlette.testclient import TestClient

    monkeypatch.setenv("GOOGLE_API_KEY", "test-key-never-persisted")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-never-persisted")
    proxy = _load_capture_proxy()
    app = proxy.build_app(
        out_dir,
        secret=_PROXY_SECRET,
        transport=httpx.MockTransport(responder),
    )
    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def _persisted_text(out_dir: pathlib.Path) -> str:
    return "\n".join(
        path.read_text("utf-8") for path in sorted(out_dir.glob("*.json"))
    )


def test_a_non_200_upstream_is_passed_through_and_never_recorded(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-09: an error body must not consume a fixture ordinal.

    Recording unconditionally meant a transient vendor 429 landed as
    `gemini-00.json` and pushed the real first turn to ordinal 01.
    """
    import httpx

    calls = {"n": 0}

    def responder(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(404, json={"error": "nope"})
        return httpx.Response(200, json={"candidates": []})

    url = _capture_url("/v1beta/models/m:generateContent")
    with _proxy_client(tmp_path, responder, monkeypatch) as client:
        first = client.post(url, json=_PROXY_BODY)
        assert first.status_code == 404
        assert first.json() == {"error": "nope"}
        assert sorted(p.name for p in tmp_path.glob("*.json")) == []

        second = client.post(url, json=_PROXY_BODY)
        assert second.status_code == 200

    # The ordinal was not consumed by the 404: the first real capture is 00.
    assert sorted(p.name for p in tmp_path.glob("*.json")) == [
        "gemini-00-request.json",
        "gemini-00.json",
    ]


def test_a_malformed_request_body_consumes_no_ordinal(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-09: a body that cannot be recorded must not claim an ordinal.

    The 13.3 residual: the ordinal was claimed before ``json.loads(body)``,
    so a malformed body returned an unhandled 500 with the ordinal already
    spent and the next real capture landing at ``gemini-01``.
    """
    import httpx

    forwarded: list[str] = []

    def responder(request: httpx.Request) -> httpx.Response:
        forwarded.append(str(request.url))
        return httpx.Response(200, json={"candidates": []})

    url = _capture_url("/v1beta/models/m:generateContent")
    with _proxy_client(tmp_path, responder, monkeypatch) as client:
        for body in (b"not json", b'["a", "list"]'):
            refused = client.post(
                url, content=body, headers={"content-type": "application/json"}
            )
            assert refused.status_code == 400
            assert "JSON object" in refused.json()["error"]

        good = client.post(url, json=_PROXY_BODY)
        assert good.status_code == 200

    # Nothing was forwarded upstream for the unrecordable bodies, and the
    # first real capture is still ordinal 00.
    assert len(forwarded) == 1
    assert sorted(p.name for p in tmp_path.glob("*.json")) == [
        "gemini-00-request.json",
        "gemini-00.json",
    ]


def test_a_request_without_the_capture_secret_is_refused(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """IN-01: the proxy must not be an open deputy for the operator's key.

    Without the secret segment, any local process — a web page issuing a
    CORS-simple POST included — could make the proxy inject the real
    `GOOGLE_API_KEY` and spend vendor credit, and could write
    attacker-controlled bodies into the fixture tree. The refusal happens
    before the key is read, before anything is forwarded, and before an
    ordinal is claimed.

    The percent-encoded shape is the WR-01 regression: `scope["path"]` is
    percent-decoded before it reaches `strip_secret`, so `%C3%A9` arrived
    as `"é"` and `secrets.compare_digest` raised `TypeError` on non-ASCII
    `str` operands — an anonymous unhandled 500 from the one function
    whose job is to refuse cleanly. `raise_server_exceptions=False` is
    what makes that 500 observable here instead of re-raised.
    """
    import httpx

    forwarded: list[str] = []

    def responder(request: httpx.Request) -> httpx.Response:
        forwarded.append(str(request.url))
        return httpx.Response(200, json={"candidates": []})

    vendor_path = "/v1beta/models/m:generateContent"
    with _proxy_client(
        tmp_path, responder, monkeypatch, raise_server_exceptions=False
    ) as client:
        for path in (
            vendor_path,
            f"/wrong-secret{vendor_path}",
            "/",
            # WR-01: a non-ASCII first segment must refuse, not crash.
            f"/%C3%A9{vendor_path}",
            # ...and a non-ASCII segment that is otherwise the secret's
            # own length, so the refusal cannot be an accident of shape.
            "/" + "é" * len(_PROXY_SECRET) + vendor_path,
        ):
            refused = client.post(path, json=_PROXY_BODY)
            assert refused.status_code == 403, (
                f"{path!r} produced {refused.status_code}, not the "
                "documented 403"
            )
            assert "capture secret" in refused.json()["error"]

        good = client.post(_capture_url(vendor_path), json=_PROXY_BODY)
        assert good.status_code == 200

    # Nothing was forwarded for the unauthenticated calls, and the first
    # real capture still lands at ordinal 00.
    assert len(forwarded) == 1
    assert sorted(p.name for p in tmp_path.glob("*.json")) == [
        "gemini-00-request.json",
        "gemini-00.json",
    ]


def test_the_default_capture_output_dir_is_never_the_committed_fixtures(
) -> None:
    """IN-02/WR-02: the default must be private, unguessable, and not fixtures.

    The original default was this committed `fixtures/` directory, so the
    no-argument invocation rewrote `anthropic-00.json` and friends in
    place. Promotion into `fixtures/` is a reviewed `mv` (D-10), not the
    easy path.

    WR-02: the IN-02 replacement was `<tempdir>/ccf-ext00-capture-<stamp>`
    at second granularity — a fully predictable path in a shared,
    world-writable directory, opened with `mkdir(exist_ok=True)`. A
    hostile local process could pre-create or symlink it and receive the
    captured vendor bodies; two same-second runs silently collided. The
    same-second assertion below is the regression that pins it, since a
    fixed timestamp is exactly what the old implementation made collide.
    """
    proxy = _load_capture_proxy()
    import datetime
    import stat

    fixed = datetime.datetime(2000, 1, 1, 0, 0, 0)  # noqa: DTZ001
    default = proxy.default_out_dir()
    created: list[pathlib.Path] = [default]
    try:
        assert default != FIXTURES
        assert FIXTURES not in default.parents
        # mkdtemp creates it; the caller never races to claim the name.
        assert default.is_dir()
        assert not default.is_symlink()
        assert sorted(default.iterdir()) == []
        if os.name == "posix":
            mode = stat.S_IMODE(default.stat().st_mode)
            assert mode == 0o700, f"expected 0o700, got {mode:#o}"

        # Two calls at the SAME instant must still be distinct directories:
        # the timestamp is decoration, mkdtemp's random suffix is the
        # uniqueness mechanism. This is the assertion the old
        # year-2000-vs-now comparison could not make.
        same_second = [proxy.default_out_dir(fixed) for _ in range(2)]
        created.extend(same_second)
        assert same_second[0] != same_second[1]
        assert default not in same_second
    finally:
        for path in created:
            shutil.rmtree(path, ignore_errors=True)


def test_a_non_json_200_is_passed_through_and_never_recorded(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-09: a 200 that is not JSON (an SSE stream, an HTML error page)."""
    import httpx

    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"data: streaming\n\n", headers={
                "content-type": "text/event-stream"
            }
        )

    with _proxy_client(tmp_path, responder, monkeypatch) as client:
        response = client.post(
            _capture_url("/v1beta/models/m:generateContent"),
            json=_PROXY_BODY,
        )

    assert response.status_code == 200
    assert response.content == b"data: streaming\n\n"
    assert list(tmp_path.glob("*.json")) == []


def test_the_query_string_is_forwarded_upstream_verbatim(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-10: dropping the query made captures unfaithful (e.g. `?alt=sse`)."""
    import httpx

    seen: list[str] = []

    def responder(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"candidates": []})

    with _proxy_client(tmp_path, responder, monkeypatch) as client:
        client.post(
            _capture_url(
                "/v1beta/models/m:generateContent?alt=sse&key=SECRETVALUE"
            ),
            json=_PROXY_BODY,
        )

    assert len(seen) == 1
    assert seen[0].startswith("https://generativelanguage.googleapis.com")
    assert "/v1beta/models/m:generateContent" in seen[0]
    assert "alt=sse" in seen[0]
    assert "key=SECRETVALUE" in seen[0]


def test_key_bearing_query_params_are_redacted_on_persist(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-10/T-13.3-04: a forwarded secret must never reach the fixtures.

    Keys ride in headers for both vendors, and headers are never written
    (T-13.2-06) — but Gemini also accepts `?key=`, so the persisted query
    is redacted and the header set stays entirely off disk.
    """
    import httpx

    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": []})

    with _proxy_client(tmp_path, responder, monkeypatch) as client:
        client.post(
            _capture_url(
                "/v1beta/models/m:generateContent?alt=sse&key=SECRETVALUE"
                "&api_key=OTHERSECRET&Key=CASEDSECRET"
                "&access_token=TOKENSECRET&X-Auth=AUTHSECRET"
            ),
            json=_PROXY_BODY,
        )

    persisted = _persisted_text(tmp_path)
    assert persisted, "nothing was captured"
    # WR-03: exact-match, case-sensitive redaction persisted `Key=`,
    # `access_token=` and friends verbatim into a git-tracked directory.
    for secret in (
        "SECRETVALUE",
        "OTHERSECRET",
        "CASEDSECRET",
        "TOKENSECRET",
        "AUTHSECRET",
    ):
        assert secret not in persisted
    assert "test-key-never-persisted" not in persisted
    # The non-secret part of the query survives; the secrets are placeheld.
    assert "alt=sse" in persisted
    for header in ("x-goog-api-key", "x-api-key", "authorization"):
        assert header not in persisted.lower()


def test_the_d15_fallback_works_with_every_client_leg_deselected() -> None:
    """WR-04: the D-15 stand-in must not depend on incidental leg ordering.

    `get_replay_record` is per-client (WR-06) and refuses a client that
    has served nothing. `run.py`'s D-15 fallback — taken whenever the
    `bare` leg is deselected — read lineage and the replay record
    directly, and worked only because every *other* leg happens to call
    `get_context` first. With no legs at all it failed with
    `AssertionError: get_replay_record refused: [...]`, which reads as an
    Experience-surface regression and sends a reader to `experience.py`
    rather than to "you deselected the leg that produces the record".

    Driving the real harness end-to-end is the only thing that would have
    caught it: the defect is an interaction between two files, invisible
    to any structural assertion over either one. `--legs ""` needs no
    replay server and no vendor key, so it costs ~1.5s.
    """
    import subprocess
    import sys

    completed = subprocess.run(
        [sys.executable, "run.py", "--legs", ""],
        cwd=EXAMPLE_DIR,
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                [str(REPO_ROOT / "src"), str(REPO_ROOT / "runtime")]
            ),
        },
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    combined = completed.stdout + completed.stderr

    assert "get_replay_record refused" not in combined, (
        "the D-15 fallback still depends on another leg having served "
        f"first:\n{combined}"
    )
    assert completed.returncode == 0, combined
    # The fallback serves itself, so PASS 5 is genuinely demonstrated
    # rather than skipped, and every later assertion still holds.
    assert "PASS 1: client legs exit 0 ()" in combined
    for pass_number in range(1, 9):
        assert f"PASS {pass_number}:" in combined, combined
