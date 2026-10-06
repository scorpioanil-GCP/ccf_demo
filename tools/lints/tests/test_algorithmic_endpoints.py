"""LOW-05 exploit test — CINV-03 sees a raw HTTP call to a model endpoint.

The row (``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``,
"LOW-05" and its MEASURED block, D-IMPL-372) measured
``tools/lints/algorithmic.py`` checking imports only, against a short vendor
denylist: a module tagged ``__ccf_mode__ = "algorithmic"`` that posts to
``https://api.anthropic.com/v1/messages`` with ``httpx`` produced ZERO
findings, and so did a ``urllib`` Bedrock call whose URL is built by
concatenation.

The repair matches **string constants** (f-string parts included) against
model-endpoint spellings. It never flags the HTTP import itself: eight shipped
algorithmic modules import ``httpx``/``urllib`` legitimately and contain no
endpoint string, so an import rule would redden all eight. The last test here
walks the real tagged roster under ``src/`` and ``runtime/`` and asserts it
stays clean, with those eight named as a positive control that the walk saw
them.

A URL read from configuration, or assembled from fragments none of which is a
model-endpoint spelling, is beyond a static lint; the lint's docstring and the
CINV-03 page say so.
"""

from __future__ import annotations

import pathlib

import pytest

from tools.lints import algorithmic
from tools.lints.__main__ import iter_python_files, module_name_for

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = pathlib.Path("src/ccf/operators/temporal.py")
MOD = "ccf.operators.temporal"
TAG = '__ccf_mode__ = "algorithmic"\n'
ENDPOINT_RULE = "cinv03-model-endpoint"

RAW_HTTP_MODEL_CALL = TAG + '''import httpx


def ask(prompt: str) -> str:
    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        json={"model": "x", "messages": [{"role": "user", "content": prompt}]},
    )
    return response.json()["content"][0]["text"]
'''

URLLIB_BEDROCK = TAG + '''import urllib.request

MODEL = "anthropic.claude"


def ask(body: bytes) -> bytes:
    url = "https://bedrock-runtime.us-east-1.amazonaws.com/model/" + MODEL + "/invoke"
    with urllib.request.urlopen(url, data=body) as r:
        return r.read()
'''

CONTROL = TAG + '''import httpx


def fetch(url: str) -> bytes:
    return httpx.get(url + "/health").content
'''


def _endpoint_findings(source: str) -> list[str]:
    return [f for f in algorithmic.check_source(source, SRC, MOD) if f.split()[1] == ENDPOINT_RULE]


def test_a_raw_http_post_to_a_model_endpoint_is_flagged() -> None:
    found = _endpoint_findings(RAW_HTTP_MODEL_CALL)
    assert len(found) == 1, found
    assert found[0].startswith(f"{SRC}:7 {ENDPOINT_RULE} ")


def test_a_concatenated_bedrock_url_is_flagged_by_its_host_fragment() -> None:
    assert len(_endpoint_findings(URLLIB_BEDROCK)) == 1


@pytest.mark.parametrize(
    "literal",
    [
        "https://api.openai.com/v1/chat/completions",
        "/v1/chat/completions",
        "/v1/responses",
        "/v1/messages",
        "models/gemini:generateContent",
        "models/gemini:streamGenerateContent",
        "/invoke-model",
        "https://generativelanguage.googleapis.com/v1beta",
        "https://us-central1-aiplatform.googleapis.com/v1/projects",
        "HTTPS://API.ANTHROPIC.COM",
    ],
)
def test_each_endpoint_spelling_is_flagged(literal: str) -> None:
    assert len(_endpoint_findings(TAG + f"URL = {literal!r}\n")) == 1


def test_an_f_string_part_is_flagged() -> None:
    source = TAG + 'def u(host):\n    return f"https://{host}/v1/messages"\n'
    assert len(_endpoint_findings(source)) == 1


def test_a_bytes_constant_is_flagged() -> None:
    assert len(_endpoint_findings(TAG + "PATH = b'/v1/chat/completions'\n")) == 1


def test_the_non_model_httpx_control_is_not_flagged() -> None:
    assert algorithmic.check_source(CONTROL, SRC, MOD) == []


def test_the_http_import_alone_is_never_flagged() -> None:
    for imp in ("import httpx\n", "import requests\n", "import urllib.request\n"):
        assert algorithmic.check_source(TAG + imp, SRC, MOD) == []


def test_an_untagged_module_may_name_an_endpoint() -> None:
    assert algorithmic.check_source('URL = "https://api.anthropic.com/v1/messages"\n', SRC, MOD) == []


def test_a_docstring_naming_an_endpoint_is_not_a_call() -> None:
    source = '"""Explains why /v1/messages is semantic-only."""\n' + TAG
    source += 'def f():\n    """Never call api.openai.com from here."""\n'
    assert algorithmic.check_source(source, SRC, MOD) == []


def test_the_endpoint_rule_id_is_distinct_from_the_import_rule() -> None:
    assert algorithmic.RULE_MODEL_ENDPOINT == ENDPOINT_RULE != algorithmic.RULE_ALGORITHMIC


#: The eight tagged modules that import an HTTP client legitimately (measured).
HTTP_IMPORTING_TAGGED = (
    "runtime/ccf_runtime/peering/typed_http.py",
    "runtime/ccf_runtime/peering/lf_a2a.py",
    "runtime/ccf_runtime/cli/main.py",
    "src/ccf/mcp/client.py",
    "src/ccf/graph/backends/fluree.py",
    "src/ccf/graph/backends/neo4j.py",
    "src/ccf/graph/backends/mongo.py",
    "runtime/ccf_runtime/http_api/gate.py",
)


def test_the_shipped_algorithmic_roster_stays_clean() -> None:
    tagged: list[str] = []
    findings: list[str] = []
    for tree in ("src", "runtime"):
        root = REPO_ROOT / tree
        for path in iter_python_files(root):
            source = path.read_text(encoding="utf-8")
            if not algorithmic.is_algorithmic(algorithmic.read_tree(source, path)):
                continue
            tagged.append(path.relative_to(REPO_ROOT).as_posix())
            findings.extend(algorithmic.check_source(source, path, module_name_for(path, root)))
    assert set(HTTP_IMPORTING_TAGGED) <= set(tagged), "the walk did not see the HTTP importers"
    assert findings == []
