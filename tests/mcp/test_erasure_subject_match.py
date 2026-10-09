"""D3b — the erasure door's server-side subject match: a verdict for the door alone, never the bytes (``D-IMPL-378``).

Dave, 2026-10-08 16:40 MST, item 5, verbatim: *"D3b: blocking against my 'fix both now' instruction. Build the
narrowly authorized server-side subject-match path without serving the bytes. Test that it creates no unauthorized
subject/existence oracle. Keep the affected erasure claim open until verified."* SEC-009 stays OPEN: this module
measures; it closes nothing.

The residual it answers: through the MCP-backed erasure door, a client filing that validates as a Decision Replay
record was refused ``subject-unverifiable``, because the artifact server answers those client-lane bytes as a missing
address and the door could not read them to verify the subject
(``tests/erasure/test_replay_input_retention_provenance.py::test_over_the_mcp_backed_store_a_record_shaped_client_filing_is_erased_like_any_client_artifact``).

What is measured here, each instrument with a positive control that shows it can see the thing it measures:

* **the bytes never cross** (``test_the_door_verifies_a_record_shaped_filing_and_the_document_never_crosses``): every
  JSON-RPC message of the door's request, both directions, blobs decoded; the control is an ordinary filing read
  through the same captured transport, whose canary the capture does see;
* **no unauthorized subject/existence oracle**, one test per caller class — no identity, another tenant's bearer,
  this tenant's reader without the grant, a principal holding the grant but not the door's key: over two worlds (the
  filings present, nothing filed) and four argument sets (an ordinary filing and a record-shaped one, a matching
  subject and another), every answer is byte-identical and the server reads nothing from its substrate (a spy);
  the control is the door itself over the same server and the same cells, which gets several distinct answers and
  reads;
* **another tenant's door learns nothing** about this tenant's address, and its substrate bytes are never read;
* **governed evidence is never judged** by the subject match: it stays behind the governed dereference;
* **parity**: the MCP-backed door reaches the in-process door's outcome for every client filing.

The timing statement (work by subject and existence for unauthorized callers) is measured by the lane's probe, not
gated here; the spy above is its deterministic half.

Tenant, principal, class, scope and token names are test deployment vocabulary, meaningful nowhere else (CINV-01
applied to test data).
"""

from __future__ import annotations

import base64
import functools
import json
import pathlib
from collections import Counter
from dataclasses import dataclass
from typing import Any

import pytest
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.mcp_store import McpArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.actions import ACTION_ARTIFACT_READ, ACTION_ARTIFACT_WRITE
from ccf.authz.capability import ArtifactErase, Execute, ReplayMint, Resume
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.erasure import ERASURE_RECORD_CLASS, DOOR_SIGNATURE_ASSERTION
from ccf.replay.record import DecisionReplayRecord
from ccf_runtime.authz.artifact import SCOPE_MAPPING, ScopeEntry, ScopeMappingArtifact
from ccf_runtime.authz.protocol import ControlPlaneTenantAuthorizer
from ccf_runtime.erasure import ErasureRefused
from ccf_runtime.mcp.artifact_server import build_artifact_server
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource, TokenGrant
from ccf_runtime.workflow.engine import WorkflowSuspended
from tests.composition import declared_erasure_trust, no_erasures, register_typed_at_composition
from tests.erasure import harness as h
from tests.erasure import signing
from tests.erasure.test_replay_input_retention_provenance import (
    RESEMBLANCE,
    _ask,
    _declaration,
    _deployment,
    _request,
)
from tests.http_api.composition_authority import WORKFLOW_TRACE_CLASS
from tests.mcp import test_sec009_mcp_names_at as names_world
from tests.mcp import wire_capture
from tests.mcp.guarded_servers import AUDIT_INSTANT, REPLAY_RECORD_CLASS, WIDE_RESOURCES, _entitlement_world
from tests.mcp.test_c2_tenant_hold_mcp import _record
from tests.replay.authority import replay_writer

TENANT = h.TENANT
FOREIGN = names_world.FOREIGN
DOOR_SCOPE = "ccf:erasure-door"
READER_SCOPE = "ccf:artifact-reader"
#: A principal the deployment granted the subject-match action by mistake — an agent, say — holding no door key.
AGENT_SCOPE = "ccf:agent-misgranted"
MAPPING_KEY = "d3b/scope-mapping"
SALT = "test-salt-not-a-secret"
OTHER_SUBJECT = "customer-99"


def _subject_match_tool() -> str:
    return str(h.contract("ccf_runtime.mcp.artifact_server", "SUBJECT_MATCH_TOOL"))


def _subject_match_action() -> str:
    return str(h.contract("ccf.authz.actions", "ACTION_ARTIFACT_SUBJECT_MATCH"))


def _refused_constant() -> str:
    return str(h.contract("ccf_runtime.mcp.artifact_server", "SUBJECT_MATCH_REFUSED"))


def _grant(client_id: str, scope: str, tenant: str = TENANT) -> TokenGrant:
    return TokenGrant(client_id=client_id, scopes=(scope,), tenants=frozenset({tenant}))


DOOR = _grant("erasure-door-service", DOOR_SCOPE)
READER = _grant("a-reader", READER_SCOPE)
AGENT = _grant("an-agent", AGENT_SCOPE)
FOREIGN_DOOR = _grant("erasure-door-service", DOOR_SCOPE, FOREIGN)


def _authorizer(subject_match_action: str) -> ControlPlaneTenantAuthorizer:
    """A real deny-by-default authorizer: the door's and the agent's scopes hold the subject-match action, the reader's does not."""
    tenants = (TENANT, FOREIGN)
    entries = {
        DOOR_SCOPE: ScopeEntry(
            tenant_patterns=tenants, action_ids=(ACTION_ARTIFACT_READ, subject_match_action), resource_patterns=WIDE_RESOURCES
        ),
        READER_SCOPE: ScopeEntry(
            tenant_patterns=tenants, action_ids=(ACTION_ARTIFACT_READ, ACTION_ARTIFACT_WRITE), resource_patterns=WIDE_RESOURCES
        ),
        AGENT_SCOPE: ScopeEntry(
            tenant_patterns=tenants, action_ids=(ACTION_ARTIFACT_READ, subject_match_action), resource_patterns=WIDE_RESOURCES
        ),
    }
    registry = ControlPlaneRegistry()
    version = register_typed_at_composition(
        registry, MAPPING_KEY, ScopeMappingArtifact(semver="1.0.0", scopes=entries), SCOPE_MAPPING
    )
    assert isinstance(version, str)
    return ControlPlaneTenantAuthorizer(
        control_plane=registry, scope_mapping_key=MAPPING_KEY, scope_mapping_version=version, clock=lambda: AUDIT_INSTANT
    )


class _Spy:
    """The substrate behind the server, counting every read the server makes of it."""

    def __init__(self, inner: FileArtifactStore) -> None:
        self._inner = inner
        self.reads: Counter[str] = Counter()

    @property
    def root(self) -> Any:
        return self._inner.root

    @property
    def write_kinds(self) -> WriteKinds:
        return self._inner.write_kinds

    def put(self, authorized: Any, artifact: Any) -> Any:
        return self._inner.put(authorized, artifact)

    def get(self, *, content_address: str) -> bytes:
        self.reads["get"] += 1
        return self._inner.get(content_address=content_address)

    def exists(self, *, content_address: str) -> bool:
        self.reads["exists"] += 1
        return self._inner.exists(content_address=content_address)

    def resolve_uri(self, *, uri: str) -> str:
        self.reads["resolve_uri"] += 1
        return self._inner.resolve_uri(uri=uri)

    def names_at(self, *, content_address: str) -> Any:
        self.reads["names_at"] += 1
        return self._inner.names_at(content_address=content_address)


def _write_kinds() -> WriteKinds:
    return WriteKinds(
        {
            WORKFLOW_TRACE_CLASS: (Execute, Resume),
            h.ERASURE_RECORD_CLASS: (ArtifactErase,),
            h.ERASURE_APPROVAL_CLASS: (ArtifactErase,),
            REPLAY_RECORD_CLASS: (ReplayMint,),
        }
    )


def _server(root: pathlib.Path, store: Any, *, authorizer: Any) -> FastMCP:
    source, recorder = _entitlement_world(root)
    return build_artifact_server(
        server_name="d3b-subject-match",
        store=store,
        token_verifier=SourceBackedTokenVerifier(source=StaticTokenSource(grants={})),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://artifact.invalid/mcp"),
            required_scopes=[DOOR_SCOPE],
        ),
        authorizer=authorizer,
        entitlement_source=source,
        refusal_recorder=recorder,
        audit_log=ControlPlaneRegistry().audit_log,
        # Both tenants declare an erasure authority, under the same test door key: the tenant
        # binding in the signed query is then the only thing that tells their doors apart.
        erasure_trust=declared_erasure_trust(TENANT, FOREIGN),
        erasure_index=no_erasures(),
        control_plane=ControlPlaneRegistry(),
    )


def _record_shaped(canary: str) -> DecisionReplayRecord:
    """A strictly valid record carrying the subject at the declared record key path and in a replay-input field."""
    base = _record(tenant=TENANT, principal=h.SUBJECT_ID, subject=canary)
    record = base.model_copy(
        update={"content_generation_path": base.content_generation_path.model_copy(update={"plan_id": h.SUBJECT_ID})}
    )
    assert DecisionReplayRecord.model_validate_json(canonical_bytes(record)) == record
    return record


ORDINARY = {"customer": {"id": h.SUBJECT_ID}, "note": "d3b ordinary client filing"}
KEY_PATHS = tuple(_declaration().subjects[0].key_paths)


@functools.cache
def _record_shaped_document() -> Any:
    """The record-shaped client filing of the oracle matrix (built on first use, not at import)."""
    return json.loads(canonical_bytes(_record_shaped("d3b-oracle-matrix")))


def _ref(identifier: str) -> str:
    return str(h.erasure("subject_ref_for")(_declaration(), h.SUBJECT_CLASS, identifier))


def _query(tenant: str, address: str, subject_ref: str) -> Any:
    return h.contract("ccf.erasure", "SubjectMatchQuery")(
        tenant_id=tenant, content_address=address, subject_ref=subject_ref, key_paths=KEY_PATHS, subject_ref_salt=SALT
    )


def _door_signature(query: Any, *, signer: Any = None) -> str:
    return str(
        h.contract("ccf.erasure", "sign_subject_match_query")(
            query, signer=signer or signing.door_provider(), key_id=signing.DOOR_KID
        )
    )


def _arguments(address: str, subject_ref: str, signature: str) -> dict[str, Any]:
    return {
        "content_address": address,
        "subject_ref": subject_ref,
        "key_paths": list(KEY_PATHS),
        "subject_ref_salt": SALT,
        "door_signature": signature,
    }


@dataclass
class _World:
    spy: _Spy
    server: FastMCP


def _world(root: pathlib.Path, *, filed: bool) -> _World:
    root.mkdir(parents=True, exist_ok=True)
    store = FileArtifactStore(root=root / "artifacts", write_kinds=_write_kinds())
    if filed:
        h.client_put(store, name="ordinary", document=ORDINARY)
        h.client_put(store, name="record-shaped", document=_record_shaped_document())
    spy = _Spy(store)
    return _World(spy=spy, server=_server(root, spy, authorizer=_authorizer(_subject_match_action())))


@functools.cache
def _cells() -> tuple[tuple[str, str], ...]:
    """The cells every caller is asked over: ``(address, subject_ref)`` — an ordinary filing and a record-shaped one,
    the subject the filings carry and another."""
    return tuple(
        (content_hash(document), _ref(subject))
        for document in (ORDINARY, _record_shaped_document())
        for subject in (h.SUBJECT_ID, OTHER_SUBJECT)
    )


@dataclass
class _Answer:
    text: str  # every server->client message, exactly as serialized
    call: str  # the server's message answering the tools/call
    reads: Counter[str]
    result: Any


def _ask_tool(world: _World, grant: TokenGrant | None, arguments: dict[str, Any]) -> _Answer:
    wire = wire_capture.Wire()
    before = Counter(world.spy.reads)
    result = wire_capture.call(world.server, grant, _subject_match_tool(), arguments, wire)
    reads = Counter(world.spy.reads)
    reads.subtract(before)
    served = "\n".join(wire.served())
    (call,) = wire.answers("tools/call")
    return _Answer(text=served, call=call, reads=+reads, result=result)


def _matrix(tmp_path: pathlib.Path) -> dict[str, _World]:
    return {"filed": _world(tmp_path / "filed", filed=True), "empty": _world(tmp_path / "empty", filed=False)}


def _door_answers(worlds: dict[str, _World]) -> dict[tuple[str, str, str], _Answer]:
    """The positive control: the door, with its genuine signature, over every world and cell."""
    return {
        (kind, address, ref): _ask_tool(world, DOOR, _arguments(address, ref, _door_signature(_query(TENANT, address, ref))))
        for kind, world in worlds.items()
        for address, ref in _cells()
    }


def _assert_the_control_sees_differences(door: dict[tuple[str, str, str], _Answer]) -> None:
    verdicts = {key: answer.result.structuredContent for key, answer in door.items()}
    assert all(not answer.result.isError for answer in door.values()), verdicts
    assert len({json.dumps(v, sort_keys=True) for v in verdicts.values()}) >= 3, verdicts
    assert all(answer.reads["get"] >= 1 for (kind, _a, _r), answer in door.items() if kind == "filed"), {
        key: dict(answer.reads) for key, answer in door.items()
    }


def _assert_one_answer_and_no_reads(answers: dict[Any, _Answer], *, naming: str) -> None:
    texts = {answer.text for answer in answers.values()}
    assert len(texts) == 1, "the answer depends on the world or the arguments:\n" + "\n".join(
        f"{key}: {answer.call[:300]}" for key, answer in answers.items()
    )
    (text,) = texts
    sample = next(iter(answers.values()))
    assert sample.result.isError is True, sample.call
    assert naming in sample.result.content[0].text, sample.result.content[0].text
    read = {key: dict(answer.reads) for key, answer in answers.items() if answer.reads}
    assert read == {}, f"the server read its substrate for an unauthorized caller: {read}"
    assert text  # an answer crossed


# --- the bytes never cross ----------------------------------------------------------------------------------------


def test_the_door_verifies_a_record_shaped_filing_and_the_document_never_crosses(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The MCP-backed door, over a real ``ClientSession`` to the built server, verifies a record-shaped client
    filing — admitted to approval, as the in-process door admits it — and in every JSON-RPC message of the request,
    both directions, blobs decoded, neither the document's canonical bytes, nor their base64, nor the canary inside
    them appear. The verdict that crossed is the subject match's, and only the verdict. Control: an ordinary filing
    read through the same captured transport — its canary is seen."""
    canary = "d3b-transport-canary-4f1c"
    plane, store = _deployment(tmp_path)
    record = _record_shaped(canary)
    filed = h.client_put(store, name="record-copy", document=json.loads(canonical_bytes(record)))
    document = canonical_bytes(record)
    assert canary.encode() in document

    server = _server(tmp_path / "server", store, authorizer=_authorizer(_subject_match_action()))
    wire = wire_capture.Wire()
    wire_capture.route_store_through(monkeypatch, server, DOOR, wire)
    client = McpArtifactStore(url="http://artifact.invalid/mcp", bridge=names_world._Run(), write_kinds=store.write_kinds)  # type: ignore[arg-type]

    outcome = _ask(h.door(plane, store=client), plane, _request(plane, filed.content_address, h.DOC_CLASS))
    assert isinstance(outcome, WorkflowSuspended), outcome

    calls = wire.requests("tools/call")
    assert [call["params"]["name"] for call in calls] == [_subject_match_tool()], calls
    (answer,) = wire.answers("tools/call")
    assert json.loads(answer)["result"]["structuredContent"] == {"verdict": "subject-in-replay-input"}, answer
    blob_reads = [r for r in wire.requests("resources/read") if r["params"]["uri"].startswith("ccf-artifact-blob://")]
    assert [r["params"]["uri"] for r in blob_reads] == [f"ccf-artifact-blob://{filed.content_address}"], blob_reads

    haystack = wire.haystack()
    assert canary.encode() not in haystack, "the record-shaped document crossed the MCP boundary"
    assert document not in haystack
    assert base64.b64encode(document) not in haystack

    control_canary = "d3b-transport-control-9a2e"
    plain = h.client_put(store, name="plain", document={"note": control_canary})
    assert client.get(content_address=plain.content_address) == canonical_bytes({"note": control_canary})
    assert control_canary.encode() in wire.haystack(), "the capture cannot see a document that does cross"


# --- no unauthorized subject/existence oracle -------------------------------------------------------------------


def test_no_identity_gets_one_answer_and_the_server_reads_nothing(tmp_path: pathlib.Path) -> None:
    """A call with no verified identity, carrying the door's GENUINE signature for each cell, gets the guard's refusal,
    byte-identical over both worlds and all four cells, and the substrate is never read. Control: the door."""
    worlds = _matrix(tmp_path)
    _assert_the_control_sees_differences(_door_answers(worlds))
    answers = {
        (kind, address, ref): _ask_tool(world, None, _arguments(address, ref, _door_signature(_query(TENANT, address, ref))))
        for kind, world in worlds.items()
        for address, ref in _cells()
    }
    _assert_one_answer_and_no_reads(answers, naming="no verified access token accompanies this call")


def test_another_tenants_bearer_gets_one_answer_and_the_server_reads_nothing(tmp_path: pathlib.Path) -> None:
    """A bearer for another tenant, holding the subject-match grant there and presenting the door's GENUINE signature
    over this tenant's query, is refused by the door-identity check — the query is rebuilt under the caller's tenant,
    which the signature does not cover, although that tenant declares an authority under the same door key — with one
    byte-identical answer over every world and cell, before anything is read. Control: the door."""
    worlds = _matrix(tmp_path)
    _assert_the_control_sees_differences(_door_answers(worlds))
    answers = {
        (kind, address, ref): _ask_tool(
            world, FOREIGN_DOOR, _arguments(address, ref, _door_signature(_query(TENANT, address, ref)))
        )
        for kind, world in worlds.items()
        for address, ref in _cells()
    }
    _assert_one_answer_and_no_reads(answers, naming=_refused_constant())


def test_a_same_tenant_caller_without_the_grant_gets_one_answer_and_the_server_reads_nothing(
    tmp_path: pathlib.Path,
) -> None:
    """This tenant's reader — ``artifact.read`` and ``artifact.write``, not the subject-match action — replaying the
    door's GENUINE signed query for each cell is refused by the deployment's authorizer before the body runs
    (``tenant-unauthorized`` naming the subject-match action), with one byte-identical answer, and nothing read.
    Control: the door."""
    worlds = _matrix(tmp_path)
    _assert_the_control_sees_differences(_door_answers(worlds))
    answers = {
        (kind, address, ref): _ask_tool(world, READER, _arguments(address, ref, _door_signature(_query(TENANT, address, ref))))
        for kind, world in worlds.items()
        for address, ref in _cells()
    }
    _assert_one_answer_and_no_reads(answers, naming=f"authorize action {_subject_match_action()!r}")


def _forged(variant: str, address: str, ref: str) -> str:
    """What a principal holding the grant but not the door's key can present for the cell ``(address, ref)``."""
    query = _query(TENANT, address, ref)
    if variant == "unsigned":
        return ""
    if variant == "garbage":
        return "not..a-signature"
    if variant == "another-key-under-the-door-key-id":
        return _door_signature(query, signer=signing.door_provider(signing.forger_door_key_dir()))
    if variant == "the-approvers-key":
        envelope = signing.provider().sign(
            product=query, key_id=signing.APPROVER_KID, assertions={DOOR_SIGNATURE_ASSERTION: "ccf.erasure-subject-match"}
        )
        return f"{envelope.protected}..{envelope.signature}"
    if variant in ("the-door-key-asserting-the-record-class", "the-door-key-asserting-the-probe-class"):
        asserted = ERASURE_RECORD_CLASS if "record" in variant else "ccf.erasure-door-probe"
        envelope = signing.door_provider().sign(
            product=query, key_id=signing.DOOR_KID, assertions={DOOR_SIGNATURE_ASSERTION: asserted}
        )
        return f"{envelope.protected}..{envelope.signature}"
    if variant == "the-doors-genuine-signature-over-another-query":
        other = next(a for a, _r in _cells() if a != address)
        return _door_signature(_query(TENANT, other, ref))
    raise AssertionError(variant)


FORGERIES = (
    "unsigned",
    "garbage",
    "another-key-under-the-door-key-id",
    "the-approvers-key",
    "the-door-key-asserting-the-record-class",
    "the-door-key-asserting-the-probe-class",
    "the-doors-genuine-signature-over-another-query",
)


def test_a_principal_holding_the_grant_but_not_the_door_key_gets_one_answer_and_the_server_reads_nothing(
    tmp_path: pathlib.Path,
) -> None:
    """A reader or agent principal of this tenant that the deployment granted the subject-match action — the
    strongest non-door caller — presenting anything but the door's signature over exactly its query: nothing, a
    malformed signature, another key under the door's key id, the approvers' key, the door's key asserting the record
    or the probe class, or the door's genuine signature over another query. Every variant, over every world and
    cell, gets the one constant refusal (``SUBJECT_MATCH_REFUSED``), byte-identical across all of them, and the
    substrate is never read. Control: the door."""
    worlds = _matrix(tmp_path)
    _assert_the_control_sees_differences(_door_answers(worlds))
    answers = {
        (variant, kind, address, ref): _ask_tool(world, AGENT, _arguments(address, ref, _forged(variant, address, ref)))
        for variant in FORGERIES
        for kind, world in worlds.items()
        for address, ref in _cells()
    }
    _assert_one_answer_and_no_reads(answers, naming=_refused_constant())


def test_another_tenants_own_door_learns_nothing_about_this_tenants_address(tmp_path: pathlib.Path) -> None:
    """Another tenant's erasure door, authorized for its own tenant and signing its own queries, asking about this
    tenant's addresses: one answer, ``subject-unverifiable``, over both worlds and every cell, and no substrate bytes
    read (the naming read is its own tenant's names). Control: when that tenant files the same bytes on its own client
    lane, its door gets a verdict about ITS filing — the path can answer it, it does not answer about this tenant's."""
    worlds = _matrix(tmp_path)
    answers = {
        (kind, address, ref): _ask_tool(
            world, FOREIGN_DOOR, _arguments(address, ref, _door_signature(_query(FOREIGN, address, ref)))
        )
        for kind, world in worlds.items()
        for address, ref in _cells()
    }
    texts = {answer.text for answer in answers.values()}
    assert len(texts) == 1, {key: answer.call[:200] for key, answer in answers.items()}
    sample = next(iter(answers.values()))
    assert sample.result.structuredContent == {"verdict": "subject-unverifiable"}, sample.call
    assert all(answer.reads["get"] == 0 for answer in answers.values()), {k: dict(a.reads) for k, a in answers.items()}

    from tests.mcp.test_sec009_mcp_names_at import _put

    theirs = _put(worlds["filed"].spy, FOREIGN, "theirs", ORDINARY)
    address, ref = theirs.content_address, _ref(h.SUBJECT_ID)
    own = _ask_tool(worlds["filed"], FOREIGN_DOOR, _arguments(address, ref, _door_signature(_query(FOREIGN, address, ref))))
    assert own.result.structuredContent == {"verdict": "subject-found"}, own.call
    assert own.reads["get"] == 1, dict(own.reads)


# --- governed evidence stays behind the governed dereference ----------------------------------------------------


def test_the_subject_match_never_judges_governed_evidence(tmp_path: pathlib.Path) -> None:
    """A record the fabric's record writer filed under this tenant — governed evidence, read only through the
    governed dereference — is never judged by the subject match: the door's genuine query for it answers
    ``subject-unverifiable`` and its bytes are never read. Control: the same door's query for an ordinary client
    filing carrying the subject is judged (``subject-found``) and its bytes are read once."""
    world = _world(tmp_path, filed=True)
    store = world.spy._inner
    record = _record_shaped("d3b-governed")
    replay_writer(store, tenant=TENANT, artifact_class=REPLAY_RECORD_CLASS).write_replay_record(record=record)
    governed = content_hash(record)
    ref = _ref(h.SUBJECT_ID)

    refused = _ask_tool(world, DOOR, _arguments(governed, ref, _door_signature(_query(TENANT, governed, ref))))
    assert refused.result.structuredContent == {"verdict": "subject-unverifiable"}, refused.call
    assert refused.reads["get"] == 0, dict(refused.reads)

    ordinary = content_hash(ORDINARY)
    judged = _ask_tool(world, DOOR, _arguments(ordinary, ref, _door_signature(_query(TENANT, ordinary, ref))))
    assert judged.result.structuredContent == {"verdict": "subject-found"}, judged.call
    assert judged.reads["get"] == 1, dict(judged.reads)


# --- parity with the in-process door ----------------------------------------------------------------------------


def _altered(root: pathlib.Path, address: str, document: Any) -> None:
    from tests.replay.test_record_content_address_integrity import _stored_file

    _stored_file(root / "artifacts", address).write_bytes(canonical_bytes(document))


def _record_at_key_path_only() -> Any:
    record = _record_shaped("d3b-parity-key-path-only")
    conditioning = record.perspective_conditioning.model_copy(update={"principal_id": "someone-else"})
    return json.loads(canonical_bytes(record.model_copy(update={"perspective_conditioning": conditioning})))


def _row(name: str, plane: Any, store: Any, root: pathlib.Path) -> str:
    if name == "ordinary, subject at a key path":
        return str(plane.document.content_address)
    if name == "ordinary, subject absent":
        return str(h.client_put(store, name="no-subject", document={"customer": {"id": OTHER_SUBJECT}}).content_address)
    if name == "ordinary, subject at a key path and in a replay-input field":
        return str(h.client_put(store, name="resemblance", document=RESEMBLANCE).content_address)
    if name == "record-shaped, subject at a key path and in a replay-input field":
        return str(h.client_put(store, name="shaped-1", document=json.loads(canonical_bytes(_record_shaped("p1")))).content_address)
    if name == "record-shaped, subject at a key path only":
        return str(h.client_put(store, name="shaped-2", document=_record_at_key_path_only()).content_address)
    if name == "record-shaped, subject absent":
        document = json.loads(canonical_bytes(_record(tenant=TENANT, principal="someone-else", subject="p3")))
        return str(h.client_put(store, name="shaped-3", document=document).content_address)
    if name == "ordinary, bytes altered under the address":
        ref = h.client_put(store, name="altered-1", document={"customer": {"id": h.SUBJECT_ID}, "note": "a"})
        _altered(root, ref.content_address, {"customer": {"id": h.SUBJECT_ID}, "note": "altered"})
        return str(ref.content_address)
    if name == "record-shaped, bytes altered under the address":
        ref = h.client_put(store, name="altered-2", document=json.loads(canonical_bytes(_record_shaped("p4"))))
        _altered(root, ref.content_address, _record_at_key_path_only())
        return str(ref.content_address)
    if name == "another tenant's filing":
        from tests.mcp.test_sec009_mcp_names_at import _put

        return str(_put(store, FOREIGN, "theirs", {"customer": {"id": h.SUBJECT_ID}, "note": "theirs"}).content_address)
    if name == "nothing filed at the address":
        return "0" * 64
    raise AssertionError(name)


#: Each client-filing row and the outcome BOTH doors must reach (``admitted`` = the approval workflow suspended).
PARITY = {
    "ordinary, subject at a key path": "admitted",
    "ordinary, subject absent": "subject-not-found",
    "ordinary, subject at a key path and in a replay-input field": "admitted",
    "record-shaped, subject at a key path and in a replay-input field": "admitted",
    "record-shaped, subject at a key path only": "admitted",
    "record-shaped, subject absent": "subject-not-found",
    "ordinary, bytes altered under the address": "subject-unverifiable",
    "record-shaped, bytes altered under the address": "subject-unverifiable",
    "another tenant's filing": "address-not-in-tenant",
    "nothing filed at the address": "address-not-in-tenant",
}


def _outcome(door: Any, plane: Any, address: str) -> str:
    try:
        outcome = _ask(door, plane, _request(plane, address, h.DOC_CLASS))
    except ErasureRefused as refused:
        return refused.reason_code
    assert isinstance(outcome, WorkflowSuspended), outcome
    return "admitted"


@pytest.mark.parametrize("row", sorted(PARITY))
def test_the_mcp_backed_door_reaches_the_in_process_doors_outcome(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, row: str
) -> None:
    """The same request through the in-process door and through the MCP-backed door — each on its own fresh plane,
    the MCP one over a real ``ClientSession`` to the built server — reaches the same outcome, and the outcome pinned
    for the row. The MCP-backed door learns nothing the in-process door does not: the same refusal code, or the same
    admission."""
    plane, store = _deployment(tmp_path / "in-process")
    in_process = _outcome(h.door(plane, store=store), plane, _row(row, plane, store, tmp_path / "in-process"))

    plane, store = _deployment(tmp_path / "over-mcp")
    address = _row(row, plane, store, tmp_path / "over-mcp")
    wire_capture.route_store_through(
        monkeypatch, names_world._server(tmp_path / "over-mcp-server", store), names_world._grant(), wire_capture.Wire()
    )
    client = McpArtifactStore(url="http://artifact.invalid/mcp", bridge=names_world._Run(), write_kinds=store.write_kinds)  # type: ignore[arg-type]
    over_mcp = _outcome(h.door(plane, store=client), plane, address)

    assert (in_process, over_mcp) == (PARITY[row], PARITY[row])


def test_a_record_the_record_writer_filed_is_refused_over_mcp_before_any_subject_match(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The one row where the doors differ, unchanged by D3b and stated rather than hidden: a record the record writer
    filed, the subject in a replay-input field. In process it is refused ``replay-input``. Over MCP the door's names
    read of an own governed address goes through the governed dereference, which does not admit the door's principal,
    so the door refuses ``class-unverifiable`` — before any read of the bytes and without asking the subject match.
    The MCP-backed door learns LESS here, never more."""
    plane, store = _deployment(tmp_path / "in-process")
    record = _record_shaped("d3b-parity-governed")
    replay_writer(store, tenant=TENANT, artifact_class=REPLAY_RECORD_CLASS).write_replay_record(record=record)
    in_process = h.door(plane, store=store)
    with pytest.raises(ErasureRefused) as refused:
        _ask(in_process, plane, _request(plane, content_hash(record), REPLAY_RECORD_CLASS))
    assert refused.value.reason_code == "replay-input"

    plane, store = _deployment(tmp_path / "over-mcp")
    replay_writer(store, tenant=TENANT, artifact_class=REPLAY_RECORD_CLASS).write_replay_record(record=record)
    wire = wire_capture.Wire()
    wire_capture.route_store_through(monkeypatch, names_world._server(tmp_path / "over-mcp-server", store), names_world._grant(), wire)
    client = McpArtifactStore(url="http://artifact.invalid/mcp", bridge=names_world._Run(), write_kinds=store.write_kinds)  # type: ignore[arg-type]
    with pytest.raises(ErasureRefused) as over_mcp:
        _ask(h.door(plane, store=client), plane, _request(plane, content_hash(record), REPLAY_RECORD_CLASS))
    assert over_mcp.value.reason_code == "class-unverifiable"
    assert wire.requests("tools/call") == []
