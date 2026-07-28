"""The A2A leg of ROADMAP criterion 4: L2 remains the only writer to L3.

CLAUDE.md §10 ("the single-writer invariant is architectural, not advisory …
this holds for A2A admissions") and §7.2 (an inbound A2A Context Product is not
admissible to L3 until the consuming Control Plane validates its Policy
bindings). Research's criterion-4 table names three observables for this
boundary, and this module is those three.

**What these tests enforce, exactly (D-21).** Three things, each narrow:

(a) With a real consuming fabric running and a real producer *process* on the
    other side, an admitted product changes the consumer's graph, and the
    change is attributable to the assembly worker — the entities that appear
    are the ones L2 resolved, under the consumer's own resolution spec.
(b) Every module shipped under ``ccf_runtime.a2a`` is scanned three ways: its
    imports reach neither the L3 graph package nor L2; no *identifier* in its
    source names a fabric write surface; and **every** transport class the
    package ships is constructed and holds no attribute, public or private,
    whose type is one. The instance scan is stated over the federation
    boundary rather than over one protocol: D-IMPL-59 makes A2A one transport
    of that boundary, so a second transport inherits this scan by being
    discovered rather than by earning a test of its own — and the D-IMPL-14
    default wire (``lf_a2a``) is inside it, not merely inside the source scan.
(c) A product the Control Plane refused leaves the consumer's L3 substrate
    byte-identical, write-ahead log included.

**What they do not enforce.** (b) is a direct-import and identifier scan over
the modules this package ships plus an attribute check on a constructed
instance of each transport class they define. It says nothing about code
reachable transitively, nothing about a transport a deployment writes itself,
and nothing about dynamically obtained attributes. (a) and (c) are observations of one exchange under one deployment's
configuration, not a statement over all inputs. Overclaiming here is the I.2
failure the retrospective flagged, so the claims are stated at the strength the
assertions actually reach and no further.

These tests *add to* ``tests/invariants/test_single_writer_boot.py`` and the
CINV-02 ``cinv02-graph-writer`` lint rule. Neither is replaced, and both must
stay green alongside this module.

**D-22 note.** ``ALLOWED_CCF_PREFIXES`` in
``tests/agents/test_consumption_discipline.py`` is deliberately untouched by
this plan. It is a direct-import allowlist over ``ccf.agents`` and it does not
scan ``ccf_runtime.a2a`` at all, which is precisely why the transport needed no
widening: the transport is not in the agents package. ``WRITE_SURFACE_NAMES``
below is *imported* from that module rather than re-listed, so the two checks
cannot drift.
"""

from __future__ import annotations

import ast
import contextlib
import importlib
import inspect
import pkgutil
import types
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

import ccf_runtime.a2a
from ccf.a2a.admission import AdmittedProduct
from ccf.products.gates import GateRefusal
from ccf_runtime.a2a.lf_a2a import LfA2AWire, build_agent_card
from ccf_runtime.a2a.typed_http import TypedHttpWire

from agents.test_consumption_discipline import WRITE_SURFACE_NAMES
from crossproc.test_a2a_exchange import (  # noqa: F401 — re-registered fixture
    FEDERATION,
    PEERS,
    TENANT,
    Consumer,
    _admit,
    _first,
    _ingest_admitted,
    _tampered,
    consumer,
    transport,
)

pytestmark = pytest.mark.crossproc

#: The fabric packages no transport module may reach. Dotted-prefix matched,
#: the way ``tools.lints.matches_module`` does it, so ``ccf.graphql`` could
#: never satisfy this by accident.
FABRIC_WRITE_PACKAGES = ("ccf.graph", "ccf.assembly")


def _transport_modules() -> tuple[types.ModuleType, ...]:
    """Every module ``ccf_runtime.a2a`` ships, discovered rather than listed.

    Discovered, because a hand-maintained list is one a later transport can be
    added without joining — and the module that joined nothing is exactly the
    one that would carry the violation.
    """
    found = [ccf_runtime.a2a]
    for info in pkgutil.walk_packages(
        ccf_runtime.a2a.__path__, prefix=ccf_runtime.a2a.__name__ + "."
    ):
        found.append(importlib.import_module(info.name))
    return tuple(found)


TRANSPORT_MODULES = _transport_modules()


def _imported_names(module: types.ModuleType) -> set[str]:
    """Every absolute module name ``module`` imports, by AST."""
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module)
    return names


def _identifiers(module: types.ModuleType) -> set[str]:
    """Every name and attribute identifier appearing in ``module``'s source.

    Identifiers, never source text. A text scan cannot tell a violation from a
    docstring that documents compliance — a module stating "this holds no graph
    write handle" would fail a grep for the type's name while being exactly
    correct. String constants are not identifiers, so they are outside this set
    and cannot trip it, and a genuine use of the type *is* an identifier and
    cannot escape it.
    """
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.alias):
            names.add(node.asname or node.name.rsplit(".", 1)[-1])
    return names


def _reaches(name: str, package: str) -> bool:
    return name == package or name.startswith(package + ".")


# --- (b) no transport module holds or names a write surface ----------------


def test_transport_modules_were_actually_discovered() -> None:
    """The scan below is only worth anything if it scanned something.

    What would fail here: a discovery helper that silently returned nothing —
    which would make every parametrized assertion below vacuously true, the
    quietest way an invariant test stops being one.
    """
    assert len(TRANSPORT_MODULES) >= 2
    assert any(
        module.__name__.endswith("typed_http") for module in TRANSPORT_MODULES
    )


@pytest.mark.parametrize(
    "module", TRANSPORT_MODULES, ids=lambda m: m.__name__
)
def test_no_transport_module_imports_the_fabric_write_packages(
    module: types.ModuleType,
) -> None:
    """CLAUDE.md §10: a transport is not a writer, and does not import one.

    What would fail here: a transport importing L2 or the graph package to
    "helpfully" ingest what it received. An import is the first step of taking
    a job that belongs to the Control Plane gate and to L2.
    """
    offending = [
        name
        for name in _imported_names(module)
        for package in FABRIC_WRITE_PACKAGES
        if _reaches(name, package)
    ]
    assert not offending, f"{module.__name__} imports {offending}"


@pytest.mark.parametrize(
    "module", TRANSPORT_MODULES, ids=lambda m: m.__name__
)
def test_no_transport_module_names_a_fabric_write_surface(
    module: types.ModuleType,
) -> None:
    """The same names ``test_consumption_discipline.py`` holds Agent to.

    What would fail here: a transport declaring a ``GraphWriter``-typed
    parameter, attribute annotation, or local — a write surface can be named
    without being imported by name, and an import scan alone would miss it.
    """
    named = _identifiers(module) & WRITE_SURFACE_NAMES
    assert not named, f"{module.__name__} names {sorted(named)}"


def _transport_classes() -> tuple[type, ...]:
    """Every ``WireProtocol``-shaped class the discovered modules define.

    Discovered structurally — a class defined in one of these modules that
    offers both halves of the seam, ``emit`` and ``receive`` — for the same
    reason :func:`_transport_modules` discovers rather than lists. A hand-listed
    pair is a pair a third transport can be added beside without joining, and
    the transport that joined nothing is the one that would carry the violation
    (advisory A1: this is exactly how ``lf_a2a``, the D-IMPL-14 *default*, came
    to be source-scanned but never instance-scanned).
    """
    found: list[type] = []
    for module in TRANSPORT_MODULES:
        for member in vars(module).values():
            if (
                isinstance(member, type)
                and member.__module__ == module.__name__
                and callable(getattr(member, "emit", None))
                and callable(getattr(member, "receive", None))
            ):
                found.append(member)
    return tuple(found)


TRANSPORT_CLASSES = _transport_classes()


def _build_typed_http(stack: contextlib.ExitStack) -> TypedHttpWire:
    """Construct the typed-HTTP transport from deployment configuration."""
    return TypedHttpWire(
        local_peer_id=PEERS["first"]["peer_id"],
        endpoints=lambda *, peer: "",
        http_client=stack.enter_context(httpx.Client()),
        clock=lambda: _SCAN_INSTANT,
        receive_path=FEDERATION["consumer"]["receive_path"],
        max_request_bytes=FEDERATION["consumer"]["max_request_bytes"],
    )


def _build_lf_a2a(stack: contextlib.ExitStack) -> LfA2AWire:
    """Construct the LF A2A transport — the D-IMPL-14 default — the same way.

    No peer is contacted and no port is bound: constructing the object is the
    whole of what this scan needs, and every value handed in comes from the
    banking fixture rather than from this module (CINV-01).
    """
    lf_values = FEDERATION["lf_a2a"]
    return LfA2AWire(
        local_peer_id=PEERS["first"]["peer_id"],
        agent_card=build_agent_card(
            name=lf_values["card"]["name"],
            version=lf_values["card"]["version"],
            description=lf_values["card"]["description"],
            rpc_url=lf_values["rpc_path"],
        ),
        cards=lambda *, peer: "",
        http_client_factory=httpx.AsyncClient,
        clock=lambda: _SCAN_INSTANT,
        rpc_path=lf_values["rpc_path"],
        max_message_bytes=FEDERATION["consumer"]["max_request_bytes"],
    )


#: The injected instant every constructed transport reads its clock from. A
#: value rather than a wall clock, because nothing here should differ run to run.
_SCAN_INSTANT = datetime(2026, 3, 1, tzinfo=UTC)

#: How each shipped transport is constructed. Keyed by the class rather than by
#: name so a rename cannot silently drop a leg, and checked for completeness
#: against :data:`TRANSPORT_CLASSES` by the count guard below.
TRANSPORT_BUILDERS: dict[
    type, Callable[[contextlib.ExitStack], Any]
] = {
    TypedHttpWire: _build_typed_http,
    LfA2AWire: _build_lf_a2a,
}


def test_every_discovered_transport_is_actually_constructed() -> None:
    """The count guard: the instance scan covers the whole discovered set.

    What would fail here: a third transport shipped without a builder, or a
    discovery helper that stopped finding one of the two that ship — either
    would shrink the instance scan silently, which is the quietest way an
    invariant test stops being one and is the same guard
    :func:`test_transport_modules_were_actually_discovered` applies to the
    source scan.
    """
    assert len(TRANSPORT_BUILDERS) == len(TRANSPORT_CLASSES), (
        f"{len(TRANSPORT_BUILDERS)} transport(s) are constructed but"
        f" {len(TRANSPORT_CLASSES)} were discovered:"
        f" built {sorted(cls.__name__ for cls in TRANSPORT_BUILDERS)},"
        f" discovered {sorted(cls.__name__ for cls in TRANSPORT_CLASSES)}"
    )
    assert set(TRANSPORT_BUILDERS) == set(TRANSPORT_CLASSES)
    assert any(
        cls.__module__.endswith("lf_a2a") for cls in TRANSPORT_CLASSES
    ), "the D-IMPL-14 default transport must be in the instance scan (A1)"


@pytest.mark.parametrize(
    "transport_class", TRANSPORT_CLASSES, ids=lambda c: c.__name__
)
def test_a_constructed_transport_holds_no_fabric_write_surface(
    transport_class: type,
) -> None:
    """The runtime counterpart of the source scans, on the objects themselves.

    Public *and* private attributes, because a source scan of a class body
    cannot see what a constructor assigned, and an object that held a writer
    under a leading underscore would hold one all the same.

    Every shipped transport, not one: this is a property of the federation
    boundary rather than of a chosen protocol, so the default wire carries the
    same evidence the fallback does (advisory A1).
    """
    builder = TRANSPORT_BUILDERS.get(transport_class)
    assert builder is not None, (
        f"{transport_class.__name__} ships without an instance scan; add its"
        " construction to TRANSPORT_BUILDERS"
    )
    with contextlib.ExitStack() as stack:
        transport = builder(stack)
        held = {
            **vars(transport),
            **{
                name: getattr(transport, name, None)
                for name in dir(transport)
                if not name.startswith("__")
            },
        }
    for name, member in held.items():
        assert type(member).__name__ not in WRITE_SURFACE_NAMES, (
            f"{transport_class.__name__}.{name} holds a fabric write surface"
            " (CLAUDE.md §10, §7.2)"
        )


# --- (a) assembly is the only mutation path --------------------------------


def test_an_admitted_product_changes_l3_only_through_assembly(
    consumer: Consumer,  # noqa: F811 — the re-registered fixture
) -> None:
    """Criterion 4, the A2A row: two heaps, one writer.

    The producer is a separate OS process with its own graph file and its own
    heap, which is what makes "the consumer holds no write handle to the
    producer's graph" literally true rather than argued (D-15).

    What would fail here: a consumer that reached L3 by any other route. The
    entities that appear carry the consumer's own minted URIs under the
    consumer's own federation entity class, so a claim that arrived any other
    way would not look like this.
    """
    before = consumer.graph_digest()
    admitted = _admit(consumer, _first(consumer, "first"))
    assert isinstance(admitted, AdmittedProduct), admitted

    unchanged_by_the_verdict = consumer.graph_digest()
    assert unchanged_by_the_verdict == before, (
        "reaching a verdict is not a write; the gate guards L2's entrance and"
        " does not shorten the path through it"
    )

    envelopes = _ingest_admitted(consumer, admitted)
    assert envelopes
    assert consumer.graph_digest() != before

    declared = FEDERATION["federation"]["entity_rule"]
    view = consumer.handle.reader.as_of(tenant_id=TENANT, at=consumer.now)
    federated = [
        record
        for record in view.entities
        if record.claim.entity_class == declared["entity_class"]
    ]
    assert len(federated) == len(admitted.product.payload["entities"])


# --- (c) a refused product leaves L3 byte-identical ------------------------


def test_a_refused_product_leaves_l3_byte_identical(
    consumer: Consumer,  # noqa: F811 — the re-registered fixture
) -> None:
    """Criterion 4, the refusal side: a turned-away product moves nothing.

    What would fail here: a consumer that ingested first and checked after, or
    a transport that had a route into L2 of its own. Either would put the
    refused message's entities into the graph and change the digest — which is
    the only way this class of violation surfaces before a replay finds history
    it cannot explain.
    """
    before = consumer.graph_digest()
    refusal = _admit(consumer, _tampered(consumer, "first"))
    after = consumer.graph_digest()

    assert isinstance(refusal, GateRefusal), refusal
    assert after == before


def test_the_consumption_discipline_allowlist_is_untouched() -> None:
    """D-22: the allowlist is not widened, and this states why it need not be.

    ``test_consumption_discipline.py`` scans ``src/ccf/agents`` only. The A2A
    transport lives in ``ccf_runtime.a2a``, which that module never reads, so
    nothing this plan added could have required an entry. What would fail here:
    someone placing transport code inside the agents package and widening the
    allowlist to make it pass — research Pitfall 7's exact scenario.
    """
    from agents import test_consumption_discipline as discipline  # noqa: PLC0415

    assert not any(
        prefix.startswith("ccf_runtime")
        for prefix in discipline.ALLOWED_CCF_PREFIXES
    )
    assert str(discipline.AGENTS_PACKAGE) == "src/ccf/agents"
