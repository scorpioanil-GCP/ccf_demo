"""The two MCP server roles are separate modules, and neither touches L3.

CLAUDE.md §7.1: "the SDK is both an MCP client and an MCP server, in more than
one role each. The SDK-as-MCP-client and SDK-as-MCP-server live in different
modules; their contracts and trust postures differ, and the artifact-persistence
role (§7.4) is distinct from the egress role." D-03 restates it as a phase
commitment, and ROADMAP criterion 1 makes it a deliverable.

Separation stated in a docstring is a convention; separation asserted by import
and source inspection is a structure. This module asserts the structure, which
is why nothing here reads prose:

===========================================  ==================================
Invariant / requirement                      What would fail here
===========================================  ==================================
role separation (§7.1, D-03, criterion 1)    the two roles would be merged into
                                             one module, or one would import the
                                             other and inherit its trust posture
scheme disjointness (T-06-16)                a live-assembly ``ccf-product://``
                                             URI could be minted by the artifact
                                             server, or an immutable artifact
                                             URI by the egress server, and a
                                             replay record could not tell which
                                             kind of address it held
ArtifactStore single-writer leg (T-06-19,    the store or its server would
CLAUDE.md §7.4, §10, criterion 4)            import or hold a graph handle, and
                                             an artifact read would have a route
                                             into L3 that did not go through L2
===========================================  ==================================
"""

from __future__ import annotations

import ast
import inspect
import types
from collections.abc import Iterator
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import pytest

import ccf.artifacts.file_store
import ccf.artifacts.mcp_store
import ccf.artifacts.protocol
import ccf_runtime.mcp.artifact_server as artifact_server
import ccf_runtime.mcp.egress as egress
from ccf.artifacts.mcp_store import McpArtifactStore
from ccf.mcp.client import SyncMcpBridge

from crossproc.conftest import spawn_child_server
from crossproc.servers.mcp_artifact_child import authorized_http_client

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

#: The graph package no artifact-side module may reach. Dotted-prefix matched,
#: the way ``tools.lints.matches_module`` does it, so ``ccf.graphql`` could
#: never satisfy this by accident.
GRAPH_PACKAGE = "ccf.graph"

#: Reused verbatim from ``tests/agents/test_consumption_discipline.py`` rather
#: than re-listed: two lists of fabric write surfaces would drift, and the one
#: that drifted would be the one nobody was watching.
from agents.test_consumption_discipline import (  # noqa: E402
    WRITE_SURFACE_NAMES,
)

ARTIFACT_CHILD = (
    Path(__file__).resolve().parents[1]
    / "crossproc"
    / "servers"
    / "mcp_artifact_child.py"
)

CALL_TIMEOUT_SECONDS = 30.0

#: Every module on the ArtifactStore side of the fabric, plus the server that
#: fronts it. The claim in CLAUDE.md §7.4 is about all of them, so the scan is.
ARTIFACT_SIDE_MODULES: tuple[types.ModuleType, ...] = (
    ccf.artifacts.protocol,
    ccf.artifacts.file_store,
    ccf.artifacts.mcp_store,
    artifact_server,
)


def _imported_names(module: types.ModuleType) -> set[str]:
    """Every absolute module name ``module`` imports, by AST.

    AST rather than ``sys.modules`` inspection: what matters is what this
    source *says*, because that is what a reviewer reads and what a lint can
    hold. A transitive import pulled in by something else is not this module's
    claim to make or break.
    """
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module)
    return names


def _reaches(name: str, package: str) -> bool:
    return name == package or name.startswith(package + ".")


# --- role separation --------------------------------------------------------


def test_the_artifact_role_and_the_egress_role_are_two_modules() -> None:
    """§7.1, D-03: distinct modules with distinct server builders.

    What would fail here: someone folding the artifact resources into
    ``egress.py`` "since they are both MCP servers". Both roles would then
    share a module, and the authenticated one would be one decorator away from
    the anonymous one.
    """
    assert artifact_server.__name__ != egress.__name__
    assert artifact_server.__file__ != egress.__file__
    assert artifact_server.build_artifact_server is not egress.build_egress_server


def test_neither_mcp_server_role_imports_the_other() -> None:
    """Separate files are not separation if one imports the other."""
    assert egress.__name__ not in _imported_names(artifact_server)
    assert artifact_server.__name__ not in _imported_names(egress)


def test_each_role_owns_its_uri_schemes_and_names_no_others() -> None:
    """T-06-16: a live address and an immutable one are never confusable.

    Asserted on both the constants and the source text. The constants are the
    behaviour; the source scan is what catches a scheme reintroduced as a
    literal somewhere the constants do not reach — a docstring example that
    someone later copies into a handler, for instance.
    """
    artifact_source = inspect.getsource(artifact_server)
    egress_source = inspect.getsource(egress)

    assert artifact_server.BLOB_URI_TEMPLATE.startswith(
        artifact_server.ARTIFACT_BLOB_URI_SCHEME + "://"
    )
    assert artifact_server.NAME_URI_TEMPLATE.startswith(
        ccf.artifacts.protocol.ARTIFACT_URI_SCHEME + "://"
    )
    assert egress.PRODUCT_URI_TEMPLATE.startswith(egress.PRODUCT_URI_SCHEME + "://")

    product_scheme = egress.PRODUCT_URI_SCHEME + "://"
    assert product_scheme not in artifact_source
    for artifact_scheme in (
        ccf.artifacts.protocol.ARTIFACT_URI_SCHEME + "://",
        artifact_server.ARTIFACT_BLOB_URI_SCHEME + "://",
        artifact_server.ARTIFACT_META_URI_SCHEME + "://",
    ):
        assert artifact_scheme in artifact_source
        assert artifact_scheme not in egress_source


# --- the ArtifactStore leg of single-writer (ROADMAP criterion 4) ----------


@pytest.mark.parametrize(
    "module", ARTIFACT_SIDE_MODULES, ids=lambda m: m.__name__
)
def test_no_artifact_side_module_imports_the_graph_package(
    module: types.ModuleType,
) -> None:
    """CLAUDE.md §7.4: the store is a substrate, never a second writer.

    What would fail here: an artifact module importing ``ccf.graph`` to
    "helpfully" re-admit a retrieved snapshot. Admission is L2's, and an import
    is the first step of taking it.
    """
    offending = [
        name for name in _imported_names(module) if _reaches(name, GRAPH_PACKAGE)
    ]
    assert not offending, f"{module.__name__} imports {offending}"


def test_the_mcp_store_holds_no_fabric_write_surface() -> None:
    """The runtime counterpart of the import scan, on the object itself.

    The import check covers the module; this covers what a deployment actually
    holds, because an attribute assigned at construction is invisible to an AST
    walk of the class's own source.
    """
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
        store = McpArtifactStore(url="http://127.0.0.1:1/mcp", bridge=bridge)
        for name in dir(store):
            if name.startswith("__"):
                continue
            member = getattr(store, name, None)
            assert type(member).__name__ not in WRITE_SURFACE_NAMES, (
                f"McpArtifactStore.{name} holds a fabric write surface "
                f"(CLAUDE.md §7.4, §10)"
            )


def test_a_full_store_cycle_leaves_the_fabric_byte_identical(
    fabric_boot: Callable[..., "FabricHandle"], tmp_path: Path
) -> None:
    """Criterion 4, T-06-19: nothing enters L3 because an artifact moved.

    The observable is the graph file's own bytes, hashed before and after a
    put/exists/resolve_uri/get cycle against a live MCP store. Hashing the file
    rather than querying the graph is deliberate: a query would only see the
    rows a reader thought to ask about, while the digest covers every byte the
    substrate holds, including any a second writer would have added.

    What would fail here: an artifact server or store that wrote through to the
    graph. The digest changes and the last assertion fires — which is the only
    way this class of violation surfaces before a replay finds interleaved
    history it cannot explain.
    """
    database_path = tmp_path / "untouched-fabric.sqlite3"
    handle = fabric_boot(database_path=database_path)
    try:
        before = sha256(database_path.read_bytes()).hexdigest()

        with _mcp_store() as store:
            ref = store.put(
                tenant_id="tenant-invariant",
                artifact_class="invariant-artifact",
                name="the-artifact",
                artifact={"label": "alpha", "ordinal": 1},
            )
            assert store.exists(content_address=ref.content_address) is True
            assert store.resolve_uri(uri=ref.uri) == ref.content_address
            assert store.get(content_address=ref.content_address)

        after = sha256(database_path.read_bytes()).hexdigest()
    finally:
        handle.close()

    assert after == before


def _mcp_store() -> Any:
    """A live ``McpArtifactStore`` and the child server behind it."""
    from contextlib import contextmanager  # noqa: PLC0415

    @contextmanager
    def running() -> Iterator[McpArtifactStore]:
        with spawn_child_server(ARTIFACT_CHILD) as port:
            with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
                yield McpArtifactStore(
                    url=f"http://127.0.0.1:{port}/mcp",
                    bridge=bridge,
                    http_client_factory=authorized_http_client,
                )

    return running()
