"""``McpArtifactStore`` under the split: the wire carries no tenant, and a shell is absence (D-IMPL-353 §1.3, §2 P5; the join).

Two client-side halves of the artifact server's split, measured without a
server: what the store SENDS on a put, and how it READS the server's two
structured answers. Every claim below is drafted from what would fail:

=====================================  =====================================
Claim                                  What would fail here
=====================================  =====================================
the put sends class, name, bytes and   a ``tenant_id`` on the wire would be a
NOT the tenant                         second source the server could be
                                       asked to honor
a shell where the bytes would be is    the client would hand a refusal shell
``ArtifactNotFound``, never the bytes  back as if it were the artifact
a shell where ``found`` would be is    the client would report an outage for a
``False``                              governed *no*
a malformed answer is still an outage  a non-server would be read as absence
=====================================  =====================================
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

import pytest

from ccf.artifacts.mcp_store import McpArtifactStore, _presence_of
from ccf.artifacts.protocol import ArtifactNotFound, WriteKinds
from ccf.authz.capability import ArtifactWrite
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.mcp.errors import McpServerUnreachable
from ccf.products.refusal import (
    RequestIdentity,
    SubjectUnavailableRefusal,
    envelope_for,
)
from tests.controlplane.capabilities import capability

TENANT = "shell-tenant"


def _shell_json() -> str:
    return canonical_bytes(
        envelope_for(
            SubjectUnavailableRefusal(cause="nonexistent", detail="x", error_code="evidence-absent"),
            request=RequestIdentity(
                product_id="ccf.evidence-dereference",
                product_version=None,
                parameters={"reference": "e" * 64},
                temporal_boundary=None,
            ),
        )
    ).decode("utf-8")


class _Bridge:
    """Runs the store's coroutine synchronously against a scripted session."""

    def __init__(self, session: Any) -> None:
        self._session = session

    def run(self, coroutine: Any) -> Any:
        import asyncio

        coroutine.close()  # the real coroutine would open a session; we script one
        return asyncio.run(self._session.pop())


class _Scripted:
    """Answers the next scripted result, remembering what was asked."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def pop(self) -> Any:
        raise AssertionError("a scripted answer is installed per test")


def _store_with(**patches: Any) -> McpArtifactStore:
    store = McpArtifactStore(
        url="http://server.invalid/mcp",
        bridge=_Bridge(_Scripted()),  # type: ignore[arg-type]
        write_kinds=WriteKinds({}),
    )
    for name, value in patches.items():
        setattr(store, name, value)
    return store


def test_the_put_sends_class_name_and_bytes_and_never_the_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    import ccf.artifacts.mcp_store as module

    sent: dict[str, Any] = {}

    class _Session:
        async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
            sent["tool"] = name
            sent["arguments"] = arguments

            class _Result:
                isError = False
                structuredContent = {
                    "content_address": content_hash({"k": 1}),
                    "uri": f"ccf-artifact://{TENANT}/c/n@" + content_hash({"k": 1}),
                    "tenant_id": TENANT,
                    "artifact_class": "c",
                    "name": "n",
                }

            return _Result()

    def run_with_session(*, url: str, operation: Any, http_client_factory: Any) -> Any:
        return operation(_Session())

    monkeypatch.setattr(module, "run_with_session", run_with_session)

    class _Run:
        def run(self, coroutine: Any) -> Any:
            import asyncio

            return asyncio.run(coroutine)

    store = McpArtifactStore(url="http://server.invalid/mcp", bridge=_Run(), write_kinds=WriteKinds({}))  # type: ignore[arg-type]
    ref = store.put(capability(ArtifactWrite, tenant=TENANT, resource="c/n"), {"k": 1})
    assert ref.tenant_id == TENANT
    assert sent["tool"] == "put_artifact"
    assert set(sent["arguments"]) == {"artifact_class", "name", "canonical_b64"}
    assert "tenant_id" not in sent["arguments"]
    assert base64.b64decode(sent["arguments"]["canonical_b64"]) == canonical_bytes({"k": 1})


def test_a_shell_where_the_bytes_would_be_is_absence_not_the_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    address = content_hash({"k": 1})
    store = _store_with()
    monkeypatch.setattr(store, "_read_blob", lambda uri: _shell_json().encode("utf-8"))
    with pytest.raises(ArtifactNotFound):
        store.get(content_address=address)


def test_the_genuine_bytes_are_returned_when_they_hash_to_the_address(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = canonical_bytes({"k": 1})
    store = _store_with()
    monkeypatch.setattr(store, "_read_blob", lambda uri: payload)
    assert store.get(content_address=hashlib.sha256(payload).hexdigest()) == payload


def test_a_shell_where_found_would_be_reads_as_false() -> None:
    assert _presence_of(_shell_json()) is False
    assert _presence_of(json.dumps({"found": True})) is True
    assert _presence_of(json.dumps({"found": False})) is False


@pytest.mark.parametrize("answer", ["not json", json.dumps({"kind": "not-a-shell"}), json.dumps({"other": 1}), json.dumps({"found": "yes"})])
def test_a_malformed_answer_is_still_an_outage(answer: str) -> None:
    with pytest.raises(McpServerUnreachable):
        _presence_of(answer)
