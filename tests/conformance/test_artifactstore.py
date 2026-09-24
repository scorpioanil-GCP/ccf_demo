"""The ``ArtifactStore`` conformance suite — the acceptance bar for every store.

CLAUDE.md §7.4 fixes the structural constraints an artifact substrate must
carry: immutable, versioned, resolvable to an *exact* version and never to
"latest", and never a second writer to the graph. D-IMPL-26 fixes the
addressing (content address as identity, versioned URI as naming). This module
asserts all of it once, parametrized over a store factory — so the MCP-backed
reference store (I.3, D-12) implements against a suite that already exists
rather than against a suite written to describe whatever it happened to build
(D-16, mirroring ``tests/conformance/test_graphstore.py``).

Two disciplines are load-bearing here:

* **Every assertion is about bytes or addresses, never about files.** A suite
  that reached for ``Path.read_bytes`` would pass on the file-backed store and
  be unimplementable against an MCP-backed one, which is the opposite of what a
  conformance suite is for. The one filesystem-shaped test in this module is
  explicitly marked as such and skipped for stores that are not file-backed.
* **"Never latest" is asserted as a refusal, not as an absence.** It is not
  enough that the Protocol has no ``resolve_latest``; a caller who *writes*
  ``@latest`` into a URI must be refused with a typed error, because the URI is
  a string and strings are where the moving target sneaks back in.

Written before the hardening it demands (D-15): the I.1 file store shipped in
04-05 with content addressing and write-once, and nothing else on this list.

I.3 (06-05) added the ``mcp`` param, and **no test body below the fixtures
changed** — which is the property ROADMAP criterion 5 actually asserts. The
only edits inside the file were the second factory branch, a non-ASCII field on
the artifact fixture, and the four MCP-specific tests appended at the end.
"""

from __future__ import annotations

import inspect
import socket
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.mcp_store import McpArtifactStore
from ccf.artifacts.protocol import (
    ArtifactNotFound,
    ArtifactStoreProtocol,
    ArtifactUriUnresolvable,
    MovingTargetRefused,
    artifact_uri,
)
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.mcp.client import SyncMcpBridge
from ccf.mcp.errors import McpServerUnreachable

from crossproc.conftest import spawn_child_server
from crossproc.servers.mcp_artifact_child import (
    authorized_http_client,
    rejected_http_client,
)

pytestmark = pytest.mark.conformance

#: Imported from the child rather than restated: the tenant a server serves
#: is the server's own deployment value, and its credential is scoped to it
#: (``SEC-018``).
from crossproc.servers.mcp_artifact_child import TENANT  # noqa: E402
ARTIFACT_CLASS = "conformance-artifact"
NAME = "the-artifact"

#: The artifact server child this suite runs its ``mcp`` param against.
ARTIFACT_CHILD = (
    Path(__file__).resolve().parents[1]
    / "crossproc"
    / "servers"
    / "mcp_artifact_child.py"
)

#: Deadline every bridged call is bounded by. A test value; the SDK chooses no
#: deadline (D-IMPL-38). Generous enough that a slow CI box is not a flake and
#: short enough that a regression to the held-session bridge fails rather than
#: hangs (06-RESEARCH.md B3).
CALL_TIMEOUT_SECONDS = 30.0


class _Artifact(CCFContract):
    """A minimal canonically-serializable artifact.

    Deliberately not one of the SDK's own contract types: the store's contract
    is byte fidelity over *any* canonical artifact, and a suite that stored
    only replay records would be testing the record.

    ``glyph`` carries non-ASCII text on **every** artifact this suite stores,
    defaulted so no test body had to change to get it. An ASCII-only fixture
    would pass against a store whose transport round-trips its payload through
    a text resource, and a store that passed on ASCII and mangled real content
    is the failure mode 06-RESEARCH.md Pitfall 4 names. With this field, that
    regression fails at the first assertion in the suite rather than in
    production.
    """

    label: str
    ordinal: int
    glyph: str = "π ≠ 3 — ünïcode ✓ 東京"


StoreFactory = Callable[[], ArtifactStoreProtocol]


@pytest.fixture(params=["file", "mcp"])
def store_factory(
    request: pytest.FixtureRequest, tmp_path: Path
) -> Iterator[StoreFactory]:
    """A factory for the store under test, one param per implementation.

    A factory rather than an instance so a test can construct two stores over
    the same substrate — which is how durability of the naming index is
    asserted without knowing what the substrate is. The ``mcp`` branch returns
    a **new client against the same running server** each call, which is what
    makes that assertion prove the *server* owns the index rather than proving
    a client cached it.
    """
    if request.param == "file":
        root = tmp_path / "artifacts"

        def factory() -> ArtifactStoreProtocol:
            return FileArtifactStore(root=root)

        yield factory
        return
    if request.param == "mcp":
        with spawn_child_server(ARTIFACT_CHILD) as port:
            with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
                url = f"http://127.0.0.1:{port}/mcp"

                def mcp_factory() -> ArtifactStoreProtocol:
                    return McpArtifactStore(
                        url=url,
                        bridge=bridge,
                        http_client_factory=authorized_http_client,
                    )

                yield mcp_factory
        return
    raise NotImplementedError(request.param)


# --- fixtures for the MCP-only properties ----------------------------------


@pytest.fixture
def artifact_server_url() -> Iterator[str]:
    """A running artifact server's endpoint."""
    with spawn_child_server(ARTIFACT_CHILD) as port:
        yield f"http://127.0.0.1:{port}/mcp"


@pytest.fixture
def bridge() -> Iterator[SyncMcpBridge]:
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as running:
        yield running


@pytest.fixture
def closed_url() -> str:
    """An endpoint nothing is listening on.

    A port bound and released, rather than a number picked out of the air: the
    OS will not hand the same one out again while this test runs, so "nothing
    answers here" is a fact rather than a hope.
    """
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return f"http://127.0.0.1:{port}/mcp"


@pytest.fixture
def store(store_factory: StoreFactory) -> ArtifactStoreProtocol:
    return store_factory()


def _put(store: ArtifactStoreProtocol, artifact: object, *, name: str = NAME):  # noqa: ANN202
    return store.put(
        tenant_id=TENANT, artifact_class=ARTIFACT_CLASS, name=name, artifact=artifact
    )


# --- content addressing ----------------------------------------------------


def test_the_address_is_the_content_hash_of_the_canonical_bytes(
    store: ArtifactStoreProtocol,
) -> None:
    """Identity is computable by anyone holding the artifact (D-IMPL-26).

    If the store assigned addresses, a consumer would have to trust the store
    to have stored what it claims. Deriving the address from the content is
    what makes the store untrusted infrastructure.
    """
    artifact = _Artifact(label="alpha", ordinal=1)
    ref = _put(store, artifact)
    assert ref.content_address == content_hash(artifact)


def test_get_returns_the_exact_canonical_bytes(store: ArtifactStoreProtocol) -> None:
    artifact = _Artifact(label="alpha", ordinal=1)
    ref = _put(store, artifact)
    assert store.get(content_address=ref.content_address) == canonical_bytes(artifact)


def test_exists_is_truthful_in_both_directions(store: ArtifactStoreProtocol) -> None:
    artifact = _Artifact(label="alpha", ordinal=1)
    assert store.exists(content_address=content_hash(artifact)) is False
    ref = _put(store, artifact)
    assert store.exists(content_address=ref.content_address) is True


def test_getting_an_unstored_address_raises_the_typed_error(
    store: ArtifactStoreProtocol,
) -> None:
    """A miss is ``ArtifactNotFound``, which is a ``KeyError`` for callers.

    Typed so a caller can distinguish "this decision's record is gone" from a
    substrate failure — the two demand opposite responses, and a bare
    ``KeyError`` from an MCP transport could mean either.
    """
    with pytest.raises(ArtifactNotFound):
        store.get(content_address=content_hash(_Artifact(label="absent", ordinal=0)))
    with pytest.raises(KeyError):
        store.get(content_address=content_hash(_Artifact(label="absent", ordinal=0)))


# --- immutability ----------------------------------------------------------


def test_re_putting_identical_content_is_a_no_op_at_the_same_address(
    store: ArtifactStoreProtocol,
) -> None:
    artifact = _Artifact(label="alpha", ordinal=1)
    first = _put(store, artifact)
    stored = store.get(content_address=first.content_address)
    second = _put(store, artifact)
    assert second.content_address == first.content_address
    assert store.get(content_address=first.content_address) == stored


def test_different_content_lands_at_a_different_address_leaving_the_first_intact(
    store: ArtifactStoreProtocol,
) -> None:
    """Overwrite is meaningless under content addressing (T-04-17).

    This is the tampering threat closed structurally: an artifact a decision
    was recorded against cannot be edited, because editing it produces a
    different artifact at a different address and leaves the recorded one
    exactly where the replay will look for it.
    """
    original = _Artifact(label="alpha", ordinal=1)
    tampered = _Artifact(label="alpha", ordinal=2)
    first = _put(store, original)
    second = _put(store, tampered)
    assert first.content_address != second.content_address
    assert store.get(content_address=first.content_address) == canonical_bytes(original)


def test_the_store_offers_no_mutation_or_removal_surface(
    store: ArtifactStoreProtocol,
) -> None:
    """There is nothing to call, which is stronger than a guard on a call."""
    for forbidden in ("update", "delete", "remove", "overwrite", "put_at", "set"):
        assert not hasattr(store, forbidden), forbidden


def test_the_store_holds_no_graph_write_surface(store: ArtifactStoreProtocol) -> None:
    """CLAUDE.md §7.4: the store is never a second writer.

    CINV-02 covers the import at lint level; this asserts the consequence at
    runtime, because the lint checks the module and this checks the object a
    deployment actually holds.
    """
    module = inspect.getmodule(type(store))
    assert module is not None
    source = inspect.getsource(module)
    assert "ccf.graph" not in source
    for forbidden in ("upsert_entity", "upsert_relationship"):
        assert not hasattr(store, forbidden), forbidden


# --- versioned-URI naming (D-IMPL-26) --------------------------------------


def test_put_returns_the_versioned_uri_carrying_the_content_address(
    store: ArtifactStoreProtocol,
) -> None:
    ref = _put(store, _Artifact(label="alpha", ordinal=1))
    assert ref.uri == artifact_uri(
        tenant_id=TENANT,
        artifact_class=ARTIFACT_CLASS,
        name=NAME,
        artifact_version=ref.content_address,
    )


def test_a_registered_uri_resolves_to_its_exact_address(
    store: ArtifactStoreProtocol,
) -> None:
    ref = _put(store, _Artifact(label="alpha", ordinal=1))
    assert store.resolve_uri(uri=ref.uri) == ref.content_address


def test_two_versions_under_one_name_each_resolve_to_their_own_address(
    store: ArtifactStoreProtocol,
) -> None:
    """Naming is many-versions-to-one-name; resolution is one-to-one.

    The whole point of the versioned URI is that the *older* version is still
    resolvable after a newer one is stored under the same name. A replay from
    two years ago resolves the artifact of two years ago.
    """
    first = _put(store, _Artifact(label="alpha", ordinal=1))
    second = _put(store, _Artifact(label="alpha", ordinal=2))
    assert store.resolve_uri(uri=first.uri) == first.content_address
    assert store.resolve_uri(uri=second.uri) == second.content_address


def test_resolving_an_unregistered_version_raises_the_typed_error(
    store: ArtifactStoreProtocol,
) -> None:
    ref = _put(store, _Artifact(label="alpha", ordinal=1))
    unregistered = artifact_uri(
        tenant_id=TENANT,
        artifact_class=ARTIFACT_CLASS,
        name=NAME,
        artifact_version=content_hash(_Artifact(label="never-stored", ordinal=9)),
    )
    with pytest.raises(ArtifactUriUnresolvable):
        store.resolve_uri(uri=unregistered)
    assert store.resolve_uri(uri=ref.uri) == ref.content_address


def test_resolving_an_unregistered_name_raises_the_typed_error(
    store: ArtifactStoreProtocol,
) -> None:
    ref = _put(store, _Artifact(label="alpha", ordinal=1))
    other_name = artifact_uri(
        tenant_id=TENANT,
        artifact_class=ARTIFACT_CLASS,
        name="never-registered",
        artifact_version=ref.content_address,
    )
    with pytest.raises(ArtifactUriUnresolvable):
        store.resolve_uri(uri=other_name)


def test_a_version_registered_under_one_name_does_not_resolve_under_another(
    store: ArtifactStoreProtocol,
) -> None:
    """Naming is scoped, so one name cannot borrow another's version.

    Without this, ``@{address}`` would be a global lookup wearing a name, and
    the tenant and artifact-class scoping in the URI would be decoration.
    """
    ref = _put(store, _Artifact(label="alpha", ordinal=1), name="first")
    borrowed = artifact_uri(
        tenant_id=TENANT,
        artifact_class=ARTIFACT_CLASS,
        name="second",
        artifact_version=ref.content_address,
    )
    with pytest.raises(ArtifactUriUnresolvable):
        store.resolve_uri(uri=borrowed)


def test_resolving_latest_is_refused_rather_than_answered(
    store: ArtifactStoreProtocol,
) -> None:
    """CLAUDE.md §7.4: replay resolves exact versions, never "latest".

    Asserted as a *refusal with a typed error*, not as a missing method. The
    URI is a string; a caller can always write ``@latest`` into it, and the
    only place that can refuse is the resolver.
    """
    _put(store, _Artifact(label="alpha", ordinal=1))
    latest = artifact_uri(
        tenant_id=TENANT,
        artifact_class=ARTIFACT_CLASS,
        name=NAME,
        artifact_version="latest",
    )
    with pytest.raises(MovingTargetRefused):
        store.resolve_uri(uri=latest)


def test_a_malformed_uri_is_refused_rather_than_guessed(
    store: ArtifactStoreProtocol,
) -> None:
    with pytest.raises(ArtifactUriUnresolvable):
        store.resolve_uri(uri="https://example.invalid/artifact@abc")


# --- durability of naming across store instances ---------------------------


def test_the_naming_index_survives_a_new_store_over_the_same_substrate(
    store_factory: StoreFactory,
) -> None:
    """A URI recorded years ago resolves against a process that never stored it.

    This is the property that makes the versioned URI usable in a replay record
    at all: the naming lives with the artifacts, not in the memory of whichever
    process happened to write them.
    """
    ref = _put(store_factory(), _Artifact(label="alpha", ordinal=1))
    reopened = store_factory()
    assert reopened.resolve_uri(uri=ref.uri) == ref.content_address
    assert reopened.get(content_address=ref.content_address) == canonical_bytes(
        _Artifact(label="alpha", ordinal=1)
    )


def test_the_store_conforms_to_the_protocol_structurally(
    store: ArtifactStoreProtocol,
) -> None:
    assert isinstance(store, ArtifactStoreProtocol)


# --- properties only a remote substrate can fail (I.3, 06-05) --------------
#
# Appended rather than folded into the parametrized suite above: a file store
# has no outage state and no credential, so asserting these against it would
# mean writing tests that pass vacuously for one param.


def test_a_missing_artifact_and_an_unreachable_server_are_distinct_types(
    artifact_server_url: str, closed_url: str, bridge: SyncMcpBridge
) -> None:
    """06-RESEARCH.md Pitfall 2, T-06-21: the two must never be one error.

    ``ArtifactStoreProtocol``'s own docstring is the reason — the two "demand
    opposite responses, and a replay that conflated them would report a missing
    record as an outage". An outage invites a retry; an absence gets written
    down as a fact about the past.

    What would fail here: a store that inferred absence from a failed read.
    That store answers ``ArtifactNotFound`` for the dead server too, both
    assertions on the last two lines collapse, and a network partition starts
    silently rewriting replay history.
    """
    missing = content_hash(_Artifact(label="never-stored", ordinal=99))

    live = McpArtifactStore(
        url=artifact_server_url,
        bridge=bridge,
        http_client_factory=authorized_http_client,
    )
    with pytest.raises(ArtifactNotFound) as absence:
        live.get(content_address=missing)

    dead = McpArtifactStore(
        url=closed_url,
        bridge=bridge,
        http_client_factory=authorized_http_client,
    )
    with pytest.raises(McpServerUnreachable) as outage:
        dead.get(content_address=missing)

    assert not isinstance(outage.value, ArtifactNotFound)
    assert not isinstance(absence.value, McpServerUnreachable)


def test_a_store_presenting_no_credential_is_refused(
    artifact_server_url: str, bridge: SyncMcpBridge
) -> None:
    """D-26, T-06-18: §7.4's "authenticated" is backed by mechanism.

    What would fail here: a server built without the verifier, or with a
    verifier its settings never install as middleware. Then the anonymous
    store reads and writes freely and this call returns instead of raising.
    """
    anonymous = McpArtifactStore(url=artifact_server_url, bridge=bridge)
    with pytest.raises(McpServerUnreachable):
        anonymous.exists(content_address=content_hash(_Artifact(label="x", ordinal=1)))


def test_a_store_presenting_a_rejected_token_is_refused_as_an_outage(
    artifact_server_url: str, bridge: SyncMcpBridge
) -> None:
    """A refusal is a fact about reaching the server, never about its contents.

    The second assertion is the load-bearing one: were a 401 to surface as
    ``ArtifactNotFound``, an expired credential would make every artifact in
    the store look deleted, and a replay would record that as history.
    """
    impostor = McpArtifactStore(
        url=artifact_server_url,
        bridge=bridge,
        http_client_factory=rejected_http_client,
    )
    with pytest.raises(McpServerUnreachable) as refusal:
        impostor.put(
            tenant_id=TENANT,
            artifact_class=ARTIFACT_CLASS,
            name=NAME,
            artifact=_Artifact(label="alpha", ordinal=1),
        )
    assert not isinstance(refusal.value, ArtifactNotFound)


def test_non_ascii_canonical_bytes_survive_the_wire_exactly(
    artifact_server_url: str, bridge: SyncMcpBridge
) -> None:
    """Pitfall 4, T-06-20: byte fidelity, asserted on bytes and on the address.

    Two assertions rather than one. Byte equality catches a transport that
    re-encoded the payload; address equality catches the subtler failure where
    the server files the artifact under an address computed from something
    other than what it stored, so a later reader hashing the bytes it got back
    computes a different one.
    """
    artifact = _Artifact(label="ünïcode ✓ 東京 — π", ordinal=7)
    store = McpArtifactStore(
        url=artifact_server_url,
        bridge=bridge,
        http_client_factory=authorized_http_client,
    )
    ref = _put(store, artifact)
    retrieved = store.get(content_address=ref.content_address)
    assert retrieved == canonical_bytes(artifact)
    assert ref.content_address == content_hash(artifact)
