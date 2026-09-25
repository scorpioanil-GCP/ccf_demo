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
from datetime import UTC, datetime
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
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ArtifactWrite
from ccf.contracts.claims import EntityClaim, LineageEntry
from ccf.mcp.client import SyncMcpBridge
from ccf.signal.envelope import SourceIdentity

from crossproc.conftest import spawn_child_server
from crossproc.servers.mcp_artifact_child import (
    TENANT as ARTIFACT_SERVER_TENANT,
)
from crossproc.servers.mcp_artifact_child import authorized_http_client
from tests.controlplane.capabilities import capability

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

#: The probe values the WAL-sensitivity test writes. Test-local drive values
#: for an instrument check — they describe nothing about any deployment and
#: name no ontology; the claim they produce is discarded with the temp file.
WAL_PROBE = {
    "tenant_id": "tenant-wal-probe",
    "entity_uri": "wal-probe://one",
    "entity_class": "wal-probe",
    "system_id": "wal-probe",
    "envelope_id": "wal-probe-envelope",
}

#: The fixed instant that write carries. Injected, like every instant in the
#: fabric: nothing here reads a wall clock.
WAL_PROBE_INSTANT = datetime(2026, 1, 1, tzinfo=UTC)

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


# --- the Experience-surface role (EXPR-01, 07-09) ---------------------------


def test_the_experience_role_is_its_own_module() -> None:
    """§7.1, T-07-22: the front door is a third module, importing neither role.

    What would fail here: someone folding the products+agents surface into
    ``egress.py`` "since they both serve products", or the experience module
    importing a sibling role and inheriting its trust posture.
    """
    import ccf_runtime.mcp.experience as experience

    assert experience.__name__ not in {egress.__name__, artifact_server.__name__}
    assert experience.__file__ not in {egress.__file__, artifact_server.__file__}
    assert experience.build_experience_server is not egress.build_egress_server

    imported = _imported_names(experience)
    assert egress.__name__ not in imported
    assert artifact_server.__name__ not in imported
    assert experience.__name__ not in _imported_names(egress)
    assert experience.__name__ not in _imported_names(artifact_server)


def test_the_experience_role_owns_its_scheme_and_names_no_others() -> None:
    """T-06-16 extended: a front-door address is not an egress or artifact one.

    Same double assertion as the two-role test above: the constants are the
    behaviour; the source scan catches a scheme reintroduced as a literal.
    """
    import ccf_runtime.mcp.experience as experience

    experience_source = inspect.getsource(experience)

    assert experience.EXPERIENCE_PRODUCT_URI_TEMPLATE.startswith(
        experience.EXPERIENCE_PRODUCT_URI_SCHEME + "://"
    )
    for foreign_scheme in (
        egress.PRODUCT_URI_SCHEME,
        ccf.artifacts.protocol.ARTIFACT_URI_SCHEME,
        artifact_server.ARTIFACT_BLOB_URI_SCHEME,
        artifact_server.ARTIFACT_META_URI_SCHEME,
    ):
        assert foreign_scheme + "://" not in experience_source

    experience_scheme = experience.EXPERIENCE_PRODUCT_URI_SCHEME + "://"
    assert experience_scheme not in inspect.getsource(egress)
    assert experience_scheme not in inspect.getsource(artifact_server)


def test_the_experience_module_imports_no_graph_package() -> None:
    """The front door holds no route into L3 (INV-CH7-10; T-07-20)."""
    import ccf_runtime.mcp.experience as experience

    offending = [
        name
        for name in _imported_names(experience)
        if _reaches(name, GRAPH_PACKAGE)
    ]
    assert not offending, f"{experience.__name__} imports {offending}"


# --- the HITL transport role (D-IMPL-20, 07-09) -----------------------------


def test_the_hitl_role_is_its_own_module() -> None:
    """§7.1, T-07-22: the authority channel is a fourth module, importing none.

    What would fail here: the HITL queues folded into the experience or
    egress module "since they are all front doors" — at which point the
    human-authority surface would be one decorator away from an anonymous
    product read.
    """
    import ccf_runtime.mcp.experience as experience
    import ccf_runtime.mcp.hitl_server as hitl_server

    siblings = (egress, artifact_server, experience)
    assert all(hitl_server.__name__ != sibling.__name__ for sibling in siblings)
    assert all(hitl_server.__file__ != sibling.__file__ for sibling in siblings)

    hitl_imports = _imported_names(hitl_server)
    for sibling in siblings:
        assert sibling.__name__ not in hitl_imports
        assert hitl_server.__name__ not in _imported_names(sibling)


def test_the_hitl_role_owns_its_scheme_and_names_no_others() -> None:
    """T-06-16 extended: a HITL queue address is confusable with no sibling's."""
    import ccf_runtime.mcp.experience as experience
    import ccf_runtime.mcp.hitl_server as hitl_server

    hitl_source = inspect.getsource(hitl_server)

    assert hitl_server.HITL_QUEUE_URI_TEMPLATE.startswith(
        hitl_server.HITL_QUEUE_URI_SCHEME + "://"
    )
    for foreign_scheme in (
        egress.PRODUCT_URI_SCHEME,
        experience.EXPERIENCE_PRODUCT_URI_SCHEME,
        ccf.artifacts.protocol.ARTIFACT_URI_SCHEME,
        artifact_server.ARTIFACT_BLOB_URI_SCHEME,
        artifact_server.ARTIFACT_META_URI_SCHEME,
    ):
        assert foreign_scheme + "://" not in hitl_source

    hitl_scheme = hitl_server.HITL_QUEUE_URI_SCHEME + "://"
    for sibling in (egress, artifact_server, experience):
        assert hitl_scheme not in inspect.getsource(sibling)


def test_the_hitl_module_imports_no_graph_package() -> None:
    """The authority channel holds no route into L3 (INV-CH7-10)."""
    import ccf_runtime.mcp.hitl_server as hitl_server

    offending = [
        name
        for name in _imported_names(hitl_server)
        if _reaches(name, GRAPH_PACKAGE)
    ]
    assert not offending, f"{hitl_server.__name__} imports {offending}"


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
        store = McpArtifactStore(
            url="http://127.0.0.1:1/mcp", bridge=bridge, write_kinds=WriteKinds({})
        )
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

    The observable is the graph substrate's own bytes, hashed before and after
    a put/exists/resolve_uri/get cycle against a live MCP store. Hashing the
    files rather than querying the graph is deliberate: a query would only see
    the rows a reader thought to ask about, while the digest covers every byte
    the substrate holds, including any a second writer would have added.

    **The digest covers the write-ahead log, not just the main file** (06-16,
    closing the item 06-09 deferred). The SQLite backend runs
    ``journal_mode = WAL`` (``src/ccf/graph/backends/sqlite.py``), so a
    committed write lands in ``<db>-wal`` and can leave the main file
    byte-identical until a checkpoint. A main-file-only digest would therefore
    have reported "byte-identical" over exactly the un-checkpointed write this
    test exists to catch — an assertion weaker than its own docstring, which is
    the same false-green family as a CI job checking a narrower path than it
    claims. The ``-shm`` index is excluded: it is process coordination state,
    not durable content, and it churns on reads. This is the digest
    ``tests/crossproc/test_peering_exchange.py`` already uses; the two now agree.

    What would fail here: an artifact server or store that wrote through to the
    graph. The digest changes and the last assertion fires — which is the only
    way this class of violation surfaces before a replay finds interleaved
    history it cannot explain.
    """
    database_path = tmp_path / "untouched-fabric.sqlite3"
    handle = fabric_boot(database_path=database_path)

    def _digest() -> str:
        """Hash the main database file and its write-ahead log together."""
        running = sha256()
        for suffix in ("", "-wal"):
            path = database_path.with_name(database_path.name + suffix)
            running.update(path.read_bytes() if path.exists() else b"")
        return running.hexdigest()

    try:
        before = _digest()

        with _mcp_store() as store:
            ref = store.put(
                # A client-lane write under a genuine capability for exactly
                # this class and name, under the tenant the child's credential
                # is scoped to (D-IMPL-353 §1.2). Writing under an arbitrary
                # tenant used to work because the credential named none at
                # all, which is `SEC-018` in one line; now the tenant is the
                # capability's and never crosses the wire (§1.3).
                capability(
                    ArtifactWrite,
                    tenant=ARTIFACT_SERVER_TENANT,
                    resource="invariant-artifact/the-artifact",
                ),
                {"label": "alpha", "ordinal": 1},
            )
            assert store.exists(content_address=ref.content_address) is True
            assert store.resolve_uri(uri=ref.uri) == ref.content_address
            assert store.get(content_address=ref.content_address)

        after = _digest()
    finally:
        handle.close()

    assert after == before


def test_the_byte_identical_digest_can_actually_see_a_committed_write(
    fabric_boot: Callable[..., "FabricHandle"], tmp_path: Path
) -> None:
    """The guard on the guard: prove the digest above is not blind.

    A byte-identical assertion is only evidence if the digest would move when
    the substrate does. The SQLite backend runs in WAL mode, and this test
    measures the consequence directly rather than reasoning about it: one
    legitimate L2 write leaves the **main file byte-identical** and changes only
    the write-ahead log. The main-file-only digest 06-09 flagged therefore could
    not have observed the very write
    ``test_a_full_store_cycle_leaves_the_fabric_byte_identical`` exists to rule
    out — it would have reported a clean fabric over a dirty one.

    What would fail here: narrowing the digest back to the main file, at which
    point ``digest_of_the_main_file_alone`` and the widened digest would agree
    and the second assertion fires. The write goes through ``AssemblyWorker``,
    the only writer, so this test asserts nothing about who may write — only
    about what the instrument can see.
    """
    database_path = tmp_path / "wal-sensitivity.sqlite3"
    handle = fabric_boot(database_path=database_path)

    def _digest(suffixes: tuple[str, ...]) -> str:
        running = sha256()
        for suffix in suffixes:
            path = database_path.with_name(database_path.name + suffix)
            running.update(path.read_bytes() if path.exists() else b"")
        return running.hexdigest()

    try:
        main_before = _digest(("",))
        both_before = _digest(("", "-wal"))
        handle.worker.admit_entity_claim(
            tenant_id=WAL_PROBE["tenant_id"],
            claim=EntityClaim(
                tenant_id=WAL_PROBE["tenant_id"],
                entity_uri=WAL_PROBE["entity_uri"],
                entity_class=WAL_PROBE["entity_class"],
                attributes={},
                observed_at=WAL_PROBE_INSTANT,
                valid_from=WAL_PROBE_INSTANT,
                lineage=frozenset(
                    {
                        LineageEntry(
                            source=SourceIdentity(
                                system_id=WAL_PROBE["system_id"]
                            ),
                            envelope_id=WAL_PROBE["envelope_id"],
                            observed_at=WAL_PROBE_INSTANT,
                        )
                    }
                ),
            ),
        )
        assert _digest(("",)) == main_before, (
            "the main file moved, so this test no longer demonstrates the"
            " blindness it exists to demonstrate — re-derive the observable"
            " before trusting the digest above"
        )
        assert _digest(("", "-wal")) != both_before
    finally:
        handle.close()


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
                    write_kinds=WriteKinds({}),
                    http_client_factory=authorized_http_client,
                )

    return running()


# --- the doors decide, and the engine does not (15.5-06) --------------------
#
# Plan 15.5-06 bound authentication, per-principal entitlement and
# grant-derived Perspective at every exposed product door. The risk that
# creates is the one 15.5-RESEARCH.md names as Pitfall 3: the check sinking
# BELOW the door — into ``run_gates``, into ``serve()``, or into the engine.
# Then the gates are impure, the local and federated gate sequences drift,
# and replay has to re-authenticate a principal who may no longer exist.
#
# These are the structural half of "the door decides".

#: ``ProjectionEngine.execute``'s parameters, as names and kinds, pinned. An
#: explicit expected tuple rather than a hash, so a diff shows a reader
#: exactly what moved. What would fail here: a contributor adding
#: ``principal_id=`` to the engine "so the projection can filter" — the whole
#: of Pitfall 3, caught here rather than in review.
#:
#: Moved once, deliberately, and the move is the decision this pin exists to
#: force: ``seeds`` joined the signature under D-IMPL-111 limb (a) (Dave,
#: 2026-08-11) so the request's entity **anchor** starts the walk. It is the
#: opposite of Pitfall 3 rather than an instance of it — the anchor is *what*
#: was asked about, never *who* asked, and the two are separated at the type
#: level: :class:`~ccf.products.request.ProductRequest` has no role, principal
#: or tenant field, and the door still resolves identity before the engine is
#: reached. The engine takes an opaque URI set and interprets none of it.
EXPECTED_EXECUTE_PARAMETERS: tuple[tuple[str, str], ...] = (
    ("self", "POSITIONAL_OR_KEYWORD"),
    ("plan", "KEYWORD_ONLY"),
    ("perspective", "KEYWORD_ONLY"),
    ("tenant_id", "KEYWORD_ONLY"),
    ("temporal_boundary", "KEYWORD_ONLY"),
    ("seeds", "KEYWORD_ONLY"),
    ("recorded_acquisitions", "KEYWORD_ONLY"),
)

#: The one place in ``src/`` a ``principal_id`` parameter is legitimate below
#: a door, with its reason. ``ProductEntitlementPolicy.grant_for`` is the
#: ARTIFACT's lookup surface — *which entitlements did the deployment declare
#: for this principal* — not a value threaded through assembly or delivery.
#: Enumerated rather than pattern-matched so a second one cannot join it
#: quietly; adding an entry is a decision a reviewer sees.
PRINCIPAL_ID_EXEMPTIONS: frozenset[tuple[str, str]] = frozenset(
    {("ccf/products/entitlement.py", "grant_for")}
)

#: The trees a principal must never reach as a function parameter.
PRINCIPAL_FREE_PACKAGES: tuple[str, ...] = (
    "ccf/products",
    "ccf/projection",
    "ccf/replay",
)

#: Every exposed Context Product door, named. The companion test below proves
#: this list is exhaustive over ``runtime/``, because a hand-listed three that
#: never checks it *is* three is how this defect happened once already: this
#: phase's first plans covered two doors and missed
#: ``ccf_runtime.mcp.experience`` — the external front door.
PRODUCT_DOOR_MODULES: tuple[str, ...] = (
    "ccf_runtime.mcp.egress",
    "ccf_runtime.mcp.experience",
    "ccf_runtime.http_api.routes.product",
)

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
RUNTIME_ROOT = Path(__file__).resolve().parents[2] / "runtime" / "ccf_runtime"

#: The two resolver seams a product door calls. A module that *calls* one is
#: serving a product; a module that merely holds one in a field (the
#: ``ApiDependencies`` bundle) or forwards one (``cli/local.py``) is not.
#:
#: Widened in shape but not in membership by plan ``15.5-15`` (``D-IMPL-108``):
#: both seams now carry the authorized :class:`~ccf.projection.plan.Perspective`
#: and the caller's typed request alongside the three strings. The set is
#: unchanged because the *role-separation* claim is unchanged — these are still
#: the two seams, still in two modules, still importing neither each other nor
#: a sibling. Nothing in this file is relaxed to accommodate the widening.
#: Widened in **membership** by plan ``17-06``: ``ServedProductResolverProtocol``
#: joins the set. It is the third resolver seam, declared in ``src/`` under
#: ``D-29`` (Amendment 1 §B) while the first two are ``runtime/``-resident — so
#: this set is a **vocabulary of resolver seams**, not a list of runtime doors,
#: and the two must not be conflated. The tree a walk covers is the walk's
#: argument; what counts as a seam is this.
PRODUCT_RESOLVER_PROTOCOLS: frozenset[str] = frozenset(
    {
        "ProductResolverProtocol",
        "ExperienceProductResolverProtocol",
        "ServedProductResolverProtocol",
    }
)

#: The ``src/``-resident product doors, and the standing record of an exemption.
#:
#: ``ccf.client.adapters.inprocess`` serves a Context Product with **no
#: principal entitlement check**, by ruling: the client surface exposes no
#: principal in v0 (``D-IMPL-129``, the v0 not-list), so there is no principal
#: for a door to entitle. That is a decision, and this tuple is where it is
#: recorded so a later reader can check it rather than infer it.
#:
#: Deliberately **not** merged into :data:`PRODUCT_DOOR_MODULES`: the two tests
#: parameterized over that tuple assert runtime-door properties this door does
#: not have and is not meant to have, and the discovery test beside them closes
#: over ``RUNTIME_ROOT`` alone. Adding this module there would fail all three
#: for the wrong reason. The equality below is what makes this an exemption of
#: exactly **one** — a second ungoverned product door under ``src/ccf/client/``
#: turns that test red in the same commit that adds it.
CLIENT_PRODUCT_DOOR_MODULES: tuple[str, ...] = ("ccf.client.adapters.inprocess",)

#: The two arguments a widened resolver seam must carry (``D-IMPL-108``), with
#: the annotation each must carry, keyed by the module that defines the seam.
#:
#: Enumerated rather than inferred so that a later "simplification" back to
#: three strings is a test failure and not a silent reopening of
#: ``DI-15.5-03``. ``perspective`` is spelled non-optionally on purpose: the
#: whole substance of that deferred item is that a resolver constructing its own
#: perspective is indistinguishable from one honouring the door's, and a
#: defaulted parameter would recreate exactly that ambiguity one layer down.
REQUIRED_RESOLVER_ARGUMENTS: tuple[tuple[str, str], ...] = (
    ("perspective", "Perspective"),
    ("request", "ProductRequest | None"),
)


def _calls_a_product_resolver(tree: ast.AST) -> bool:
    """Whether this module *invokes* a product-resolver seam.

    **Three** shapes now, each drawn from what a shipped door actually does
    rather than from what a door might hypothetically do:

    1. a **parameter** annotated with one of the resolver Protocols, then
       called — the two MCP doors and the HTTP route;
    2. an attribute literally named ``product_resolver``, called on a
       dependency bundle — the same three, reached through ``ApiDependencies``;
    3. an **annotated assignment** whose annotation names a resolver Protocol,
       then called by that name — added by plan ``17-06`` for
       ``ccf.client.adapters.inprocess``, which holds
       ``_resolver: ServedProductResolverProtocol`` as a class-body annotation
       and calls ``self._resolver(...)``.

    Shape 3 is required rather than convenient, and the reason is worth stating
    where the code is: the client adapter obtains its resolver from a
    ``binding.yaml`` factory and checks it with ``isinstance``, so there is no
    annotated *parameter* anywhere in that module and no attribute named
    ``product_resolver``. **Without shape 3, a walk over ``src/ccf/client/``
    discovers the empty set** — and an equality against an empty discovered set
    is a gate that passes while checking nothing, which is precisely the
    failure this module was built to be immune to. The adapter's half of that
    contract is pinned at the adapter, by
    ``tests/client/test_inprocess_adapter.py::test_the_adapter_holds_its_resolver_in_an_annotated_attribute``,
    because a detector reshaped after the fact to match whatever landed proves
    nothing.

    **Holding a seam is still not serving through it.** All three shapes
    require a *call*, which is why ``dependencies.py`` (a dataclass field) and
    ``cli/local.py`` (a keyword argument) remain correctly absent, and why a
    module that annotates a resolver and never invokes it is not a door.
    """
    seam_names: set[str] = set()
    for node in ast.walk(tree):
        annotation: ast.expr | None = None
        name: str | None = None
        if isinstance(node, ast.arg):
            annotation, name = node.annotation, node.arg
        elif isinstance(node, ast.AnnAssign) and isinstance(
            node.target, ast.Name
        ):
            annotation, name = node.annotation, node.target.id
        if annotation is None or name is None:
            continue
        unparsed = ast.unparse(annotation)
        if any(protocol in unparsed for protocol in PRODUCT_RESOLVER_PROTOCOLS):
            seam_names.add(name)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in seam_names:
            return True
        if isinstance(func, ast.Attribute) and (
            func.attr == "product_resolver" or func.attr in seam_names
        ):
            return True
    return False


def _discover_product_doors(root: Path, package: str) -> set[str]:
    """Every module under ``root`` that serves a Context Product.

    **Takes its root as a parameter**, and that is the whole reason this is a
    function rather than a comprehension inlined in one test. A discovery walk
    pinned to a fixed path cannot be sabotaged without editing the real tree and
    reverting, which leaves nothing behind and proves nothing on any later run.
    Parameterized, a control writes a second resolver-calling module into a
    ``tmp_path`` tree and calls **this same function** on it.

    Raises:
        AssertionError: ``root`` does not exist, or holds no ``.py`` files at
            all. A walk that returns the empty set because it walked nothing is
            indistinguishable from a tree with no doors, and the second is the
            answer this function exists to give. Failing loudly on the first is
            what keeps every equality below non-vacuous.
    """
    assert root.is_dir(), f"discovery root does not exist: {root}"
    modules = sorted(root.rglob("*.py"))
    assert modules, f"discovery root holds no Python modules: {root}"
    return {
        _module_name_for(path, root, package)
        for path in modules
        if _calls_a_product_resolver(ast.parse(path.read_text(encoding="utf-8")))
    }


def _module_name_for(path: Path, root: Path, package: str) -> str:
    """``<root>/a/b.py`` → ``<package>.a.b``."""
    parts = list(path.relative_to(root).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join([package, *parts])


def test_the_projection_engines_execute_signature_is_unchanged() -> None:
    """Replay determinism rests on this signature; pin it explicitly.

    What would fail here: any parameter added, removed, renamed, or moved
    between keyword-only and positional. A door that wanted to push a
    principal into the engine would have to change this line first, and the
    change would then be a decision somebody made rather than one that
    happened.
    """
    from ccf.projection.engine import ProjectionEngine

    observed = tuple(
        (name, parameter.kind.name)
        for name, parameter in inspect.signature(
            ProjectionEngine.execute
        ).parameters.items()
    )

    assert observed == EXPECTED_EXECUTE_PARAMETERS


@pytest.mark.parametrize("package", PRINCIPAL_FREE_PACKAGES)
def test_no_principal_id_parameter_exists_below_the_door(package: str) -> None:
    """Pitfall 3, as a test rather than as a warning sign.

    An AST walk over every function in the assembly, delivery and replay
    trees. What would fail here: ``run_gates(..., principal_id=...)``,
    ``serve(..., principal_id=...)``, or a projection that filtered by
    caller — at which point the gates become impure, the local and federated
    gate sequences drift, and a replay of a departed principal cannot run.

    ``Perspective.principal_id`` is a model FIELD, not a function parameter,
    and is deliberately untouched: the door resolves it and the engine
    receives it already resolved. That is the shape this test defends, not
    the one it forbids.
    """
    offending: list[str] = []
    for path in sorted((SRC_ROOT / package).rglob("*.py")):
        relative = path.relative_to(SRC_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            names = [
                argument.arg
                for argument in (
                    *node.args.posonlyargs,
                    *node.args.args,
                    *node.args.kwonlyargs,
                )
            ]
            if "principal_id" not in names:
                continue
            if (relative, node.name) in PRINCIPAL_ID_EXEMPTIONS:
                continue
            offending.append(f"{relative}::{node.name}")

    assert not offending, (
        f"a principal_id parameter appears below the door in {offending};"
        " entitlement is decided at the door and the engine receives an"
        " already-resolved Perspective (15.5-RESEARCH.md Pitfall 3)"
    )


def test_replay_feeds_the_recorded_perspective_and_resolves_none() -> None:
    """A principal who no longer exists must still replay (T-15.5-25).

    Two halves, and both are needed. The engine must CONSTRUCT its
    ``Perspective`` from the record's dimension-4 content — the positive
    claim — and no perspective resolver may be reachable from the replay tree
    at all, the negative one. Either half alone passes against a module that
    reads the record and then "refreshes" the role from somewhere current.
    """
    import importlib

    import ccf.replay.engine as replay_engine

    source = inspect.getsource(replay_engine)
    assert "Perspective(" in source
    assert "record.perspective_conditioning.principal_id" in source
    assert "record.perspective_conditioning.role" in source

    for path in sorted((SRC_ROOT / "ccf" / "replay").rglob("*.py")):
        module = importlib.import_module(
            _module_name_for(path, SRC_ROOT, "")[1:]
        )
        offending = [
            name
            for name in _imported_names(module)
            if name.startswith("ccf_runtime")
            or "product_entitlement" in name
        ]
        assert not offending, (
            f"{path.name} reaches {offending}; replay resolves no"
            " perspective and re-authenticates nobody"
        )


@pytest.mark.parametrize("module_name", PRODUCT_DOOR_MODULES)
def test_every_product_door_entitles_after_it_authenticates(
    module_name: str,
) -> None:
    """Each door reaches the shared decision, and each sits behind auth.

    The entitlement claim is on the *shared* function rather than on each
    door's own inlined checks, because that is the property worth defending:
    three doors reaching one definition of "entitled". That the shared
    function reaches the artifact's two raising checks is asserted once,
    below.

    The authentication claim differs by surface and says so. The two MCP
    doors construct their own ``FastMCP`` with ``token_verifier`` and
    ``auth``; the HTTP route sits behind ``create_app``'s ``auth=`` hook and
    therefore asserts the composition it actually depends on — reading the
    verified grant off the request through the shared, fail-closed helper.
    """
    import importlib

    module = importlib.import_module(module_name)
    source = inspect.getsource(module)

    # `D-IMPL-256` (3), `24.6-16`: a door may reach the shared decision either
    # DIRECTLY or through the governed delivery-boundary step that wraps it.
    # `ccf_runtime.authz.delivery_boundary.govern_entitlement` calls
    # `entitled_perspective` itself and adds the determination's replay and
    # disclosure, so a door calling it reaches exactly the same definition of
    # "entitled" — one layer up. The property defended here is unchanged (the
    # doors share ONE definition); what moved is which layer of that one
    # definition each door is entitled to call. The transitive half is
    # asserted below, so widening the needle does not widen the claim.
    reaches_the_decision = ("entitled_perspective(", "govern_entitlement(")
    assert any(needle in source for needle in reaches_the_decision), (
        f"{module_name} serves a product without reaching the shared"
        f" entitlement decision by any of {list(reaches_the_decision)}"
        " (15.5-06; D-IMPL-256 (3))"
    )
    if "entitled_perspective(" not in source:
        # The wrapper is not a second reading of "entitled": it reaches the
        # same one. Without this, the widened needle above would admit a door
        # that called something merely NAMED `govern_entitlement`.
        import ccf_runtime.authz.delivery_boundary as boundary

        assert "entitled_perspective(" in inspect.getsource(boundary), (
            "the governed delivery-boundary step no longer reaches the shared"
            " entitlement decision, so a door calling it is not entitled"
        )
    assert "from ccf_runtime.authz.product_entitlement import" in source, (
        f"{module_name} does not import the shared seams; three doors with"
        " three readings of 'entitled' is the drift this import prevents"
    )

    if module_name.startswith("ccf_runtime.mcp."):
        assert "token_verifier=token_verifier" in source
        assert "auth=auth_settings" in source
    else:
        assert "grant_from_request(" in source


def test_the_shared_decision_reaches_the_artifacts_two_raising_checks() -> None:
    """The one place ``require_schema`` and ``require_role`` are called.

    Asserted once, on the shared source, because that is where the order
    lives. What would fail here: a refactor that "simplified" the source to
    check the class and forget the role — which no door-side test would
    catch, since every door would still be reaching the shared function.
    """
    import ccf_runtime.authz.product_entitlement as shared

    source = inspect.getsource(shared)
    assert "grant_for(" in source
    assert "require_schema(" in source
    assert "require_role(" in source


def test_the_product_door_table_is_exhaustive_over_the_runtime_tree() -> None:
    """A fourth door cannot ship ungated — it fails here instead.

    This is the assertion this phase's own planning needed and did not have.
    The first plans enumerated the doors by hand and missed
    ``ccf_runtime.mcp.experience`` — the external front door, and the least
    excusable one to miss. A hand-listed three that never checks it *is*
    three is exactly how that happens, so the table above is checked against
    the tree rather than trusted.

    "Product-serving" is mechanical: a module that *calls* a product-resolver
    seam. Merely holding one is not serving through it, which is why the
    ``ApiDependencies`` bundle and the CLI's local composition are correctly
    absent.
    """
    discovered = _discover_product_doors(RUNTIME_ROOT, "ccf_runtime")

    assert discovered == set(PRODUCT_DOOR_MODULES), (
        "the declared product-door table disagrees with the runtime tree;"
        f" declared={sorted(PRODUCT_DOOR_MODULES)}"
        f" discovered={sorted(discovered)} — a door added without an entry"
        " would otherwise ship ungated (T-15.5-21b)"
    )


# --- CLNT-19: the in-process client door, and the one exemption it carries ---
#
# Plan `17-06`. The client seam serves a Context Product with no principal
# entitlement check, by ruling (`D-IMPL-129`, the v0 not-list). The gate built
# in 15.5 so that *"a fourth door fails the suite"* walked `runtime/` only, so
# it would have stayed green while exactly the thing it exists to catch shipped
# in `src/`. It now walks the client tree too, with the exemption **named,
# asserted, and singular**.
#
# The positive assertion comes first on purpose. Every equality below is
# vacuous if the detector cannot see the adapter at all, and a walk that
# discovers the empty set satisfies an equality against an empty declared tuple
# — which is the Phase 15.1 Gate 2 shape and the single most likely way this
# ships broken.

CLIENT_ROOT = SRC_ROOT / "ccf" / "client"


def test_the_detector_sees_the_in_process_adapter() -> None:
    """The positive assertion, before any equality — and it is the load-bearing one.

    If ``_calls_a_product_resolver`` cannot see the real adapter, everything
    below passes over an empty set and this file resumes protecting nothing
    while reporting green. That is not hypothetical: the adapter obtains its
    resolver from a ``binding.yaml`` factory and checks it with ``isinstance``,
    so it has no annotated *parameter* and no attribute named
    ``product_resolver`` — the two shapes this detector matched before plan
    ``17-06`` widened it.
    """
    import ccf.client.adapters.inprocess as adapter

    tree = ast.parse(inspect.getsource(adapter))

    assert _calls_a_product_resolver(tree) is True, (
        "the product-door detector does not see"
        " ccf.client.adapters.inprocess, so the exhaustiveness equality below"
        " would close over the empty set and this gate would protect nothing"
    )


def test_the_client_tree_holds_exactly_the_named_unentitled_door() -> None:
    """`CLNT-19`. One exemption, recorded — and a second one fails here.

    Equality rather than membership, for the reason the runtime table beside it
    uses equality: a hand-listed one that never checks it *is* one is how a
    second ungoverned door ships. ``make ci-core`` reads this every run, so the
    day a second product-serving module appears under ``src/ccf/client/``, this
    test goes red in the same commit that adds it.
    """
    discovered = _discover_product_doors(CLIENT_ROOT, "ccf.client")

    assert discovered, (
        "the client tree discovered no product door at all — the walk found"
        " nothing to check, which is a broken detector rather than a clean tree"
    )
    assert discovered == set(CLIENT_PRODUCT_DOOR_MODULES), (
        "the declared client product-door table disagrees with the tree;"
        f" declared={sorted(CLIENT_PRODUCT_DOOR_MODULES)}"
        f" discovered={sorted(discovered)}. This door serves with no principal"
        " entitlement check by ruling (D-IMPL-129); a SECOND one doing so is"
        " not covered by that ruling and needs its own"
    )


def test_the_client_door_is_not_in_the_runtime_door_table() -> None:
    """The two tables stay two, and the reason is not tidiness.

    ``PRODUCT_DOOR_MODULES`` is parameterized by two tests asserting properties
    the client adapter deliberately does not have — that each door reaches
    ``entitled_perspective`` and sits behind authentication — and the runtime
    discovery test closes over ``RUNTIME_ROOT`` alone. Merging the tables would
    fail all three for the wrong reason, and "the wrong reason" is how a real
    finding gets muted by an unrelated red.
    """
    assert not set(CLIENT_PRODUCT_DOOR_MODULES) & set(PRODUCT_DOOR_MODULES)
    assert all(name.startswith("ccf_runtime.") for name in PRODUCT_DOOR_MODULES)
    assert all(
        name.startswith("ccf.client.") for name in CLIENT_PRODUCT_DOOR_MODULES
    )


# --- the controls: the discovery walk must be able to fail ------------------


def _write_module(root: Path, name: str, body: str) -> None:
    """Plant a module in a throwaway tree the real walk will then read."""
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_control_a_second_calling_door_is_discovered(tmp_path: Path) -> None:
    """Control 1: a second module that *calls* an annotated seam is found.

    Passed into the **real** :func:`_discover_product_doors` rather than into a
    re-implementation of it, so what is proven is that the shipped walk fires.
    """
    _write_module(tmp_path, "__init__.py", "")
    _write_module(
        tmp_path,
        "intruder.py",
        "from ccf.products.resolver import ServedProductResolverProtocol\n\n\n"
        "class SecondDoor:\n"
        "    _resolver: ServedProductResolverProtocol\n\n"
        "    def serve(self):\n"
        "        return self._resolver(tenant='t')\n",
    )

    discovered = _discover_product_doors(tmp_path, "fake")

    assert "fake.intruder" in discovered
    assert discovered != set(CLIENT_PRODUCT_DOOR_MODULES), (
        "a second unentitled door did not break the exemption equality"
    )


def test_control_holding_a_seam_without_calling_it_is_not_a_door(
    tmp_path: Path,
) -> None:
    """Control 2: the deliberate **non**-failure, and it is as load-bearing.

    "Holding is not serving" is the property that keeps ``ApiDependencies`` off
    the runtime table. A detector that flagged every module mentioning a
    resolver Protocol would discover half the tree and the equality would fail
    for reasons nobody could act on — so this control asserts the walk stays
    quiet here, and a control that only ever proves a gate fires cannot catch
    that.
    """
    _write_module(tmp_path, "__init__.py", "")
    _write_module(
        tmp_path,
        "bystander.py",
        "from ccf.products.resolver import ServedProductResolverProtocol\n\n\n"
        "class Bundle:\n"
        "    resolver: ServedProductResolverProtocol\n\n"
        "    def hand_it_over(self):\n"
        "        return self.resolver\n",
    )

    discovered = _discover_product_doors(tmp_path, "fake")

    assert discovered == set(), (
        "a module that merely holds a resolver was counted as serving through"
        f" it: {sorted(discovered)}"
    )


def test_control_the_other_call_shape_is_also_discovered(tmp_path: Path) -> None:
    """Control 3: a bare annotated local, called by name, is found too.

    The adapter uses the attribute shape (``self._resolver(...)``). This proves
    the widening covers the other spelling as well, so a later refactor of the
    adapter from a field to a local does not silently take this door out of the
    gate's view.
    """
    _write_module(tmp_path, "__init__.py", "")
    _write_module(
        tmp_path,
        "local_shape.py",
        "from ccf.products.resolver import ServedProductResolverProtocol\n\n\n"
        "def serve(factory):\n"
        "    resolver: ServedProductResolverProtocol = factory()\n"
        "    return resolver(tenant='t')\n",
    )

    discovered = _discover_product_doors(tmp_path, "fake")

    assert "fake.local_shape" in discovered


def test_control_the_discovery_walk_refuses_an_empty_or_absent_root(
    tmp_path: Path,
) -> None:
    """Control 4: the walk goes RED when it cannot walk, never quiet.

    This is the control the other three do not cover, and the one this project
    has been bitten by three times: a discovery gate whose subject moves,
    disappears, or resolves to nothing does not report "no doors" — it reports
    a passing equality against the empty set. Both failure modes raise here
    instead.
    """
    with pytest.raises(AssertionError, match="does not exist"):
        _discover_product_doors(tmp_path / "absent", "fake")

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(AssertionError, match="no Python modules"):
        _discover_product_doors(empty, "fake")


# --- DI-15.5-03: the perspective a door authorized is the one it forwards ---
#
# Closed by plan `15.5-15` under `D-IMPL-108`. Three assertions, in ascending
# strength, because the weak ones alone are what let the gap live for two
# waves: the seam has the parameter (shape), no door discards the decision
# (source), and the value that arrives is the value that was authorized
# (behaviour). Only the third would have failed against the shipped defect.


@pytest.mark.parametrize(
    ("module_name", "protocol_name"),
    (
        ("ccf_runtime.mcp.egress", "ProductResolverProtocol"),
        ("ccf_runtime.mcp.experience", "ExperienceProductResolverProtocol"),
    ),
)
def test_both_resolver_seams_require_the_perspective_and_the_request(
    module_name: str, protocol_name: str
) -> None:
    """Shape: five keyword-only arguments, and neither new one defaulted.

    What would fail here: a well-meaning later change giving ``perspective`` a
    ``None`` default "for compatibility". That single edit would restore
    DI-15.5-03 exactly — a resolver could then be handed nothing and construct
    its own, and no test of status codes or served bytes anywhere in this tree
    would notice.
    """
    import importlib

    module = importlib.import_module(module_name)
    signature = inspect.signature(getattr(module, protocol_name).__call__)

    for name, annotation in REQUIRED_RESOLVER_ARGUMENTS:
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty, (
            f"{module_name}.{protocol_name} defaults {name!r}; the seam"
            " requires the value, because a default is indistinguishable"
            " from the deployment constructing its own (DI-15.5-03)"
        )
        assert str(parameter.annotation).replace("'", "") == annotation


@pytest.mark.parametrize("module_name", PRODUCT_DOOR_MODULES)
def test_no_door_discards_what_entitled_perspective_returned(
    module_name: str,
) -> None:
    """Source: every call to the shared decision binds its result.

    The shipped defect was literally ``entitled_perspective(...)`` as a bare
    expression statement — the decision computed, the refusal honoured, the
    answer thrown away. This walks each door's AST for that shape rather than
    grepping for prose, so the assertion is about the code and not about the
    comment above it.

    **Both spellings of the callee.** The three shipped doors import the name,
    so an ``ast.Name``-only match holds on today's shape and only on today's
    shape: a door written ``product_entitlement.entitled_perspective(...)`` —
    an ``ast.Attribute`` callee — discards exactly as much and would not have
    tripped. A guard whose subject can be rewritten without changing what the
    guard observes is the defect class ``DI-15.5-06`` names for the surface
    manifest; it is cheaper to close here than to record. Found by the Phase
    15.5 close-time cross-AI panel (`15.5-CLOSE-REVIEWS.md`, finding C4).
    """
    import importlib

    module = importlib.import_module(module_name)
    tree = ast.parse(inspect.getsource(module))

    def _callee_name(call: ast.Call) -> str | None:
        function = call.func
        if isinstance(function, ast.Name):
            return function.id
        if isinstance(function, ast.Attribute):
            return function.attr
        return None

    discarded = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and _callee_name(node.value) == "entitled_perspective"
    ]

    assert not discarded, (
        f"{module_name} calls entitled_perspective for its refusal alone at"
        f" line(s) {discarded} and discards what it decided; the door then"
        " proves that an unentitled caller was refused while leaving unproven"
        " that the product it served was shaped under the perspective it"
        " authorized (DI-15.5-03, D-IMPL-108)"
    )


def test_the_perspective_the_egress_door_authorized_reaches_the_resolver(
    tmp_path: Path,
) -> None:
    """Behaviour: the VALUE, observed on the real door, over the real auth.

    The assertion this whole item was missing. The two above would both pass
    against a door that forwarded ``Perspective(principal_id=..., role=...)``
    freshly constructed from the URI — which is a different security property
    from forwarding what the entitlement decided, and is indistinguishable
    from it in every byte the consumer sees.

    So: stand the authenticated egress server up in process, read one product
    through it as a verified and entitled caller, and compare what the
    resolver received against what this deployment's perspective seam returned
    for that grant. Identity of value, not presence of parameter.

    What would fail here: a door re-deriving the perspective after the
    decision, forwarding a different principal's, or resolving the product
    before the decision ran.
    """
    from crossproc.test_mcp_egress import (
        LOCAL_PRINCIPAL,
        LOCAL_ROLE,
        LOCAL_TOKEN,
        _local_world,
        _read_in_process,
        build_servable_product,
    )
    from ccf.projection.plan import Perspective
    from ccf_runtime.mcp.egress import product_uri

    assembled = build_servable_product(
        database_path=tmp_path / "perspective-forwarding.sqlite3"
    )
    forwarded: list[tuple[Perspective, object]] = []
    server, _entitlement, _registry = _local_world(
        tmp_path,
        servable=assembled.served,
        address=assembled.address,
        forwarded=forwarded,
    )

    served, _body = _read_in_process(
        server,
        product_uri(
            tenant=assembled.address.tenant,
            product_class=assembled.address.product_class,
            version=assembled.address.version,
        ),
        token=LOCAL_TOKEN,
    )

    assert served is True
    assert len(forwarded) == 1
    perspective, request = forwarded[0]
    assert perspective == Perspective(
        principal_id=LOCAL_PRINCIPAL, role=LOCAL_ROLE
    )
    # And the honest absence: this surface's URI carries no query segment, so
    # the door passes no request rather than manufacturing one (CINV-01 — a
    # subject, an intent and a freshness figure the SDK invented would be
    # deployment values in library code).
    assert request is None
