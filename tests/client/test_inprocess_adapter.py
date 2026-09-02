"""`D-13`, `D-16`, `D-30` — the degenerate wire, its cache, and what cannot cross it.

Three properties carry this module, and each is asserted the way it is for a
reason worth stating once:

**The caching tests count boots. They never time them.** A timing-based caching
test passes on a fast machine with no cache at all, which makes it a test of the
machine. The counter below wraps the real
:func:`~ccf.deployment.config.load_config_and_boot` the adapter calls, so what
it counts is the thing that would raise.

**The cache-key tests use two *spellings of one root*, not two roots.** That is
`D-30`'s actual failure mode rather than a tidiness concern, and it was measured
rather than reasoned about: a second boot against one graph raises
``SingleWriterViolation: a GraphWriter already exists for graph
'…/graph.sqlite3'``. A cache keyed on the literal address string passes every
other test in this file and fails the first time an adopter writes an absolute
path.

**The leak test walks the result, rather than checking a field.** `D-13`'s claim
is that no live producer-side object can cross the seam *at all* — not that the
fields a reader thought of are clean — so the assertion has to be a reachability
walk over what a caller actually holds.
"""

from __future__ import annotations

import ast
import inspect
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.client.adapters import inprocess
from ccf.client.adapters.inprocess import SCHEME, InProcessAdapter
from ccf.client.binding import SCHEME_REGISTRY
from ccf.client.client import ProductClient
from ccf.client.codec import decode_outcome
from ccf.client.errors import RefusedResultError
from ccf.client.result import Result
from ccf.client.wire import WireRequest
from ccf.contracts.canonical import canonical_bytes
from ccf.deployment import BootedFabric
from ccf.products.gates import ServableProduct
from ccf.products.request import ProductRequest
from ccf.replay.serve import ServedProduct

from tests.client.conftest import SEEDED_ROWS, config_document

#: The one declared parameter the fixture's request contract requires.
THRESHOLD = "minimum_score"

#: A pinned instant for the legs that assert a *stable* answer.
#:
#: `BL-02` (Phase 17 close review, ruled by Dave 2026-08-16) made `as_of=None`
#: mean **now** instead of a literal declared in `binding.yaml`. Every test
#: below that compares two content addresses, or asserts a debt signal, was
#: reproducible only because the declared literal happened to be fixed — it was
#: measuring assembly while inheriting determinism from config. Under a real
#: clock those legs compare clocks, and the fixture's seeded observations sit
#: near this instant, so asking "now" reports them five months stale and the
#: debt signal moves. Pinning is what makes each assertion about its own
#: subject again. The `as_of=None` path has its own coverage below.
_PINNED = datetime(2026, 3, 2, 12, 0, tzinfo=UTC)


class _BootCounter:
    """Counts the boots the adapter actually performs.

    Wraps the real function rather than replacing it, so the adapter behaves
    identically and what is observed is *whether* a boot happened — never a
    duration, and never a stand-in for one.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.count = 0
        real = inprocess.load_config_and_boot

        def counted(*args: Any, **kwargs: Any) -> BootedFabric:
            self.count += 1
            return real(*args, **kwargs)

        monkeypatch.setattr(inprocess, "load_config_and_boot", counted)


@pytest.fixture()
def boots(monkeypatch: pytest.MonkeyPatch) -> Iterator[_BootCounter]:
    """A live count of boots performed through the adapter's own call site."""
    yield _BootCounter(monkeypatch)


def _client(root: Path | str) -> ProductClient:
    """A client bound to a deployment root over the in-process scheme."""
    return ProductClient.for_product(
        _product_id(root) if isinstance(root, Path) else "fixture.widgets-over-score",
        binding=f"{SCHEME}:{root}",
    )


def _product_id(root: Path) -> str:
    """The class the fixture deployment declares, read from its own document."""
    return str(config_document(root)["product_class"]["schema_name"])


# ---------------------------------------------------------------------------
# Behaviour 1 — a first ask boots and answers.
# ---------------------------------------------------------------------------


def test_a_first_ask_boots_the_fabric_and_returns_a_result(
    seeded_root: Path, boots: _BootCounter
) -> None:
    """One command's worth of client code gets a Result out of a deployment.

    The four post-assembly fields are asserted together because a Result that
    carried a payload and no content address would satisfy a narrower test
    while being useless for exactly the audit story the client exists to serve.
    """
    result = _client(seeded_root).ask(parameters={THRESHOLD: 20}, as_of=_PINNED)

    assert boots.count == 1
    assert not result.refused
    assert result.payload["count"] == 2
    assert [widget["name"] for widget in result.payload["widgets"]] == [
        "beta",
        "gamma",
    ]
    assert result.payload["assembled"] == len(SEEDED_ROWS)
    assert result.debt.signal.value == "ok"
    assert len(result.content_address) == 64
    assert result.replay_ref.startswith("ccf-artifact://")


# ---------------------------------------------------------------------------
# Behaviour 2 — a second ask does not re-boot, and does not raise.
# ---------------------------------------------------------------------------


def test_a_second_ask_on_one_client_does_not_reboot(
    seeded_root: Path, boots: _BootCounter
) -> None:
    """`D-30`. The cache is what makes the second question legal at all.

    Without it this is not "slower" — it raises
    :class:`~ccf.graph._writer.SingleWriterViolation`, because a second
    ``load_config_and_boot`` against one graph is a second writer.
    """
    client = _client(seeded_root)

    first = client.ask(parameters={THRESHOLD: 20})
    second = client.ask(parameters={THRESHOLD: 60})

    assert boots.count == 1, "the second ask re-booted the fabric"
    assert first.payload["count"] == 2
    assert second.payload["count"] == 1


# ---------------------------------------------------------------------------
# Behaviour 3 — two clients on one binding share one fabric.
# ---------------------------------------------------------------------------


def test_two_clients_on_one_binding_share_one_fabric(
    seeded_root: Path, boots: _BootCounter
) -> None:
    """`D-30`. Sharing is what makes the second client legal, not what makes it fast.

    There is no ``close()`` on ``ProductClient`` by ruling, and this is why: a
    per-client close would retire a handle the other client is still using.
    """
    first = _client(seeded_root)
    second = _client(seeded_root)

    first_result = first.ask(parameters={THRESHOLD: 20}, as_of=_PINNED)
    second_result = second.ask(parameters={THRESHOLD: 20}, as_of=_PINNED)

    assert boots.count == 1, "the second client booted its own fabric"
    assert first_result.content_address == second_result.content_address


# ---------------------------------------------------------------------------
# Behaviour 4 — two different deployments are two fabrics.
# ---------------------------------------------------------------------------


def test_two_deployment_roots_boot_two_fabrics(
    seeded_root: Path, tmp_path: Path, boots: _BootCounter
) -> None:
    """The cache is keyed, not global — two deployments are two entries.

    The negative half of every test above: a cache that returned one fabric for
    any address would pass all of them and serve the wrong deployment's answer.
    """
    import shutil

    from tests.client.conftest import seed

    second_root = tmp_path / "second-deployment"
    shutil.copytree(seeded_root, second_root)
    (second_root / "graph.sqlite3").unlink()
    seed(second_root, rows=(("delta", "99"),))

    _client(seeded_root).ask(parameters={THRESHOLD: 20})
    second = _client(second_root).ask(parameters={THRESHOLD: 20})

    assert boots.count == 2, "two deployment roots shared one cache entry"
    assert [widget["name"] for widget in second.payload["widgets"]] == ["delta"]


# ---------------------------------------------------------------------------
# Behaviour 5 — the relative and absolute spellings of one root are ONE entry.
# ---------------------------------------------------------------------------


def test_a_relative_and_absolute_root_are_one_cache_entry(
    seeded_root: Path, boots: _BootCounter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`D-30`'s real failure mode, asserted rather than intended.

    ``./deployment`` and the absolute path it resolves to name **one graph**.
    A cache keyed on the literal address string would boot twice against that
    graph and raise ``SingleWriterViolation`` — with a message naming the graph
    file, which tells an adopter nothing about the absolute path they just
    typed being the cause.
    """
    monkeypatch.chdir(seeded_root.parent)
    relative = f"./{seeded_root.name}"

    first = _client(relative).ask(parameters={THRESHOLD: 20}, as_of=_PINNED)
    second = _client(seeded_root).ask(parameters={THRESHOLD: 20}, as_of=_PINNED)

    assert boots.count == 1, (
        "the relative and absolute spellings of one deployment root booted"
        " twice — a second boot against one graph is a SingleWriterViolation"
    )
    assert first.content_address == second.content_address


# ---------------------------------------------------------------------------
# Behaviour 6 — a redundant path segment resolves to the same entry.
# ---------------------------------------------------------------------------


def test_a_redundant_path_segment_is_the_same_cache_entry(
    seeded_root: Path, boots: _BootCounter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same rule, second spelling: ``./a/../deployment`` is ``./deployment``.

    Included because "resolve the path" and "normalise the string" are
    different operations, and only one of them collapses this.
    """
    monkeypatch.chdir(seeded_root.parent)
    (seeded_root.parent / "sibling").mkdir()
    redundant = f"./sibling/../{seeded_root.name}"

    _client(redundant).ask(parameters={THRESHOLD: 20})
    _client(seeded_root).ask(parameters={THRESHOLD: 20})

    assert boots.count == 1, "a redundant path segment produced a second entry"


# ---------------------------------------------------------------------------
# Behaviour 7 — a bad question comes back as a refused Result.
# ---------------------------------------------------------------------------


def test_a_question_the_class_does_not_answer_is_a_refused_result(
    seeded_root: Path,
) -> None:
    """`D-07`. A refusal is the fabric working, so it is a value and not a raise.

    And the six guarded fields raise on a refused result rather than reading as
    ``None``: a caller who skipped the ``refused`` branch is told so, instead of
    recording an absent payload as an answer.
    """
    result = _client(seeded_root).ask(parameters={})

    assert result.refused
    assert result.refusal.kind == "product-request-violation"
    for field in ("payload", "debt", "content_address", "replay_ref"):
        with pytest.raises(RefusedResultError):
            getattr(result, field)


# ---------------------------------------------------------------------------
# Behaviour 8 — the vessel on the wire IS the canonical bytes.
# ---------------------------------------------------------------------------


def test_the_wire_carries_exactly_the_canonical_bytes_of_the_vessel(
    seeded_root: Path,
) -> None:
    """`D-13`. The round trip is real, not a re-wrapped live object.

    Asserted by computing ``canonical_bytes`` **independently** of the adapter
    and comparing: an adapter that handed its live product onward and let the
    decoder re-serialize it would satisfy a weaker assertion about equal
    payloads while having skipped the wire entirely.
    """
    adapter = InProcessAdapter(str(seeded_root))
    request = WireRequest(
        product_id=_product_id(seeded_root),
        parameters={THRESHOLD: 20},
        temporal_boundary=_PINNED,
    )
    # The seam carries bytes (`C-08`), so the one decoder turns them back into
    # the one outcome shape. `decode_outcome` returns a `DecodedOutcome` pair;
    # the outcome is `.outcome` and the vessel it already parsed is `.vessel`.
    outcome = decode_outcome(adapter.ask(request), sent=request).outcome

    booted = inprocess._BOOT_CACHE[seeded_root.resolve()]
    declared = booted.document.question
    served = booted.resolver(
        tenant=booted.fabric.tenant_id,
        product_class=request.product_id,
        version=config_document(seeded_root)["product_class"]["schema_version"],
        perspective=booted.document.perspective,
        request=ProductRequest(
            schema_name=request.product_id,
            schema_version=booted.schema_version,
            subject=declared.subject,
            intent=declared.intent,
            freshness=declared.freshness,
            asked_at=_PINNED,
            parameters={THRESHOLD: 20},
        ),
    )
    assert isinstance(served, ServedProduct)

    assert outcome.product_json == canonical_bytes(served.product).decode("utf-8")
    assert isinstance(outcome.product_json, str), (
        "the vessel rides as utf-8 text; `17-04` ruled there is no bytes field"
    )


def test_the_question_half_crosses_the_wire_too(seeded_root: Path) -> None:
    """`C-07`. The echo is what the door PARSED, not the object it was handed.

    The answer half has been a degenerate wire since ``D-13``; until Phase 19
    the **question** half was not, and that is what made the client's echo
    cross-check cosmetic on the transport every quickstart, fixture and dev
    path uses. The adapter now encodes the question, and a producer-side door
    half parses it and echoes what it parsed.

    Observed through the echo rather than by inspecting the adapter, because
    the property is *"the question crossed"* and not *"a particular method was
    called"*. Two assertions carry it and both are needed: total equality says
    nothing was lost or coerced on the way across (``C-03``), and non-identity
    says a round trip actually happened — an adapter that passed its argument
    straight through to the door would satisfy equality perfectly and is the
    exact design ``C-07`` rejects.

    The parameter carries a **nested mapping** on purpose. That is
    ``D-IMPL-103``'s one declared level of nesting, and it is the shape a
    lossy wire mangles first — which is why
    :meth:`~ccf.products.door.WireRequest._parameters_survive_the_wire` exists
    and why it became load-bearing the moment this comparison could fail.

    The fixture **refuses** this question (``nested`` is undeclared, and the
    declared world is closed), and that is not incidental: the echo sits at
    outcome level, so one comparison covers a served answer and a refusal
    identically (``C-04``). A crossed refusal is a governed "no" attributed to
    a question nobody asked, and this asserts it is as detectable as a crossed
    vessel.
    """
    adapter = InProcessAdapter(str(seeded_root))
    nested = {"widget_ref": "w-1", "note": "one declared level"}
    request = WireRequest(
        product_id=_product_id(seeded_root),
        parameters={THRESHOLD: 20, "nested": nested},
        temporal_boundary=_PINNED,
    )

    decoded = decode_outcome(adapter.ask(request), sent=request).outcome

    assert decoded.refusal is not None, (
        "the fixture closes its declared world, so an undeclared parameter is"
        " refused — if this became a served answer the leg below would be"
        " asserting the echo of a different shape than it claims to"
    )
    assert decoded.request == request, (
        "the echo is the question the door parsed off its own wire, compared by"
        " total equality (`C-03`) — a difference here is a lossy wire, which is"
        " what `_parameters_survive_the_wire` exists to stop"
    )
    assert decoded.request is not request, (
        "the echo is the SAME OBJECT the client sent, so the question half is"
        " not a wire at all and the cross-check compares an object with itself"
        " — `D-IMPL-151` finding `B0`, surviving in-process"
    )
    assert decoded.request.parameters["nested"] == nested


def test_an_absent_boundary_is_echoed_absent_though_the_door_answered_at_one(
    seeded_root: Path,
) -> None:
    """`C-02`/`C-15`. Two different facts, and neither is derived from the other.

    ``as_of=None`` is the positive assertion *answer against the decision
    instant*, so the echo must come back ``None``: an echo carrying the
    resolved instant would force a sent-``None`` to match anything, which is
    the vacuity ``C-02`` rejected one field over. The instant the answer was
    actually computed at is not lost by that — it is reported on the served
    vessel, which is where a caller reads it.
    """
    adapter = InProcessAdapter(str(seeded_root))
    request = WireRequest(
        product_id=_product_id(seeded_root),
        parameters={THRESHOLD: 20},
        temporal_boundary=None,
    )

    # Bound WITHOUT `.outcome` here, because this leg reads the vessel as well:
    # `decode_outcome` returns the `DecodedOutcome` pair, whose outcome is
    # `.outcome` and whose already-parsed vessel is `.vessel`. `decoded.request`
    # would be an attribute error on the pair — deliberately loud rather than
    # silently wrong.
    decoded = decode_outcome(adapter.ask(request), sent=request)

    assert decoded.outcome.request.temporal_boundary is None
    assert decoded.vessel is not None, (
        "a served answer, so there is a vessel to read the decision instant off"
        " — on a refusal the second half of this leg would be vacuous"
    )
    assert isinstance(decoded.vessel.temporal_boundary, datetime), (
        "the door answered at a concrete instant and says so on the vessel;"
        " nothing about the echo being `None` makes the decision instant"
        " unauditable"
    )


# ---------------------------------------------------------------------------
# Behaviour 9 — nothing live crosses the seam.
# ---------------------------------------------------------------------------


def _reachable(root: object, *, limit: int = 4000) -> list[object]:
    """Every object reachable from ``root`` by attribute and container walk.

    Deliberately broad — fields, ``__dict__`` entries, ``__slots__`` entries,
    and the contents of every mapping and sequence — because `D-13`'s claim is
    about what a caller *holds*, not about the fields a test author thought to
    check.
    """
    seen: dict[int, object] = {}
    queue: list[object] = [root]
    while queue and len(seen) < limit:
        current = queue.pop()
        if id(current) in seen:
            continue
        seen[id(current)] = current
        if isinstance(current, (str, bytes, int, float, bool, type(None))):
            continue
        if isinstance(current, dict):
            queue.extend(current.keys())
            queue.extend(current.values())
            continue
        if isinstance(current, (list, tuple, set, frozenset)):
            queue.extend(current)
            continue
        for name in getattr(type(current), "__slots__", ()):
            if hasattr(current, name):
                queue.append(getattr(current, name))
        for value in vars(current).values() if hasattr(current, "__dict__") else ():
            queue.append(value)
    return list(seen.values())


def test_no_live_producer_side_object_is_reachable_from_the_result(
    seeded_root: Path,
) -> None:
    """`D-13`'s guarantee, and it is structural rather than conventional.

    A ``BootedFabric``, a ``ServedProduct`` and a ``ServableProduct`` cannot
    survive a round trip through UTF-8 text — which is exactly why the adapter
    serializes objects it already holds. This walk is what makes the claim
    checkable rather than asserted.
    """
    result = _client(seeded_root).ask(parameters={THRESHOLD: 20})

    forbidden = (BootedFabric, ServedProduct, ServableProduct)
    leaked = [
        obj for obj in _reachable(result) if isinstance(obj, forbidden)
    ]

    assert not leaked, (
        "a live producer-side object is reachable from the Result:"
        f" {[type(obj).__name__ for obj in leaked]}"
    )


def test_the_leak_walk_finds_a_planted_producer_object(seeded_root: Path) -> None:
    """The control for the walk above — it must be able to fail.

    A reachability walk that returned nothing would pass the leak test on a
    Result that leaked everything. Planting a real ``ServedProduct`` behind the
    same walk is what proves the assertion has teeth, and it is passed into the
    **same** ``_reachable`` the shipped assertion uses rather than a copy.
    """
    result = _client(seeded_root).ask(parameters={THRESHOLD: 20})
    booted = inprocess._BOOT_CACHE[seeded_root.resolve()]

    planted = {"result": result, "leak": booted.fabric}
    leaked = [
        obj for obj in _reachable(planted) if isinstance(obj, BootedFabric)
    ]

    assert leaked, "the reachability walk cannot see a planted BootedFabric"


# ---------------------------------------------------------------------------
# Behaviour 10 — the adapter's code shape, asserted where the file is owned.
# ---------------------------------------------------------------------------


def test_the_adapter_holds_its_resolver_in_an_annotated_attribute() -> None:
    """The shape the product-door exhaustiveness gate matches on.

    ``tests/invariants/test_mcp_role_separation.py`` discovers a product door by
    matching seam names against ``PRODUCT_RESOLVER_PROTOCOLS``, and one shape it
    matches is an annotated assignment whose annotation names a resolver
    Protocol. **An adapter holding its resolver any other way is invisible to
    the gate that exists to see exactly this door**, and the gate would pass
    while checking nothing.

    Asserted here, in the module that owns ``inprocess.py``, rather than in the
    gate — a detector reshaped after the fact to match whatever landed proves
    nothing, so the subject's half of the contract is pinned where the subject
    is written.
    """
    tree = ast.parse(inspect.getsource(inprocess))

    annotated = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "_resolver"
        and "ServedProductResolverProtocol" in ast.unparse(node.annotation)
    ]
    assert annotated, (
        "`_resolver: ServedProductResolverProtocol` is not an annotated"
        " assignment in the adapter — the exhaustiveness gate would not see"
        " this door"
    )

    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_resolver"
    ]
    assert calls, "the adapter never calls `self._resolver(...)`"


# ---------------------------------------------------------------------------
# Registration, and the scheme the whole design turns on.
# ---------------------------------------------------------------------------


def test_the_inprocess_scheme_is_registered_at_import() -> None:
    """`D-05`. A scheme reaches the registry by its module being imported.

    ``17-05`` shipped ``SCHEME_REGISTRY`` deliberately empty; this is the plan
    that populates it, and there is still no plugin lookup and no discovery
    chain behind it.
    """
    assert SCHEME_REGISTRY[SCHEME] is InProcessAdapter


def test_a_binding_naming_no_deployment_refuses_when_it_is_asked(
    tmp_path: Path,
) -> None:
    """Construction is cheap; the refusal arrives at the question.

    Deliberate: a client built against a root that does not exist yet should
    fail when it asks, which is when the deployment was actually needed.
    """
    from ccf.client.errors import BindingError

    client = ProductClient.for_product(
        "fixture.widgets-over-score", binding=f"{SCHEME}:{tmp_path / 'absent'}"
    )

    with pytest.raises(BindingError):
        client.ask(parameters={THRESHOLD: 20})


def test_an_explicit_as_of_reaches_the_deployment(seeded_root: Path) -> None:
    """`D-04`. Naming an instant asks the question against that moment.

    The fixture's rows are fixed instants, so a boundary before them assembles
    nothing — which is a different answer from the pinned boundary's, and that
    difference is the whole observable proof the boundary crossed the seam.

    What "assembles nothing" looks like moved in ``24.5-L-24``. It used to be
    a SERVED product carrying ``"assembled": 0`` with the scorer's ``D_c`` of
    1 routing to ``fail_closed`` — advisory, a number about a graph that said
    nothing. The returned-empty half of the empty-operator gate
    (:data:`ccf.products.gates.GATE_EMPTY_OPERATOR_RESULT`) now makes that
    fail-closed structural on the governed path: the one operator returned an
    empty set, so the fabric REFUSES by name rather than serving an empty
    answer, and the refusal — not a payload — is what carries the boundary
    across the seam. The pinned boundary beside it is the positive control:
    the same question, an instant the rows exist at, serves every row.
    """
    before = datetime(2020, 1, 1, tzinfo=UTC)

    result = _client(seeded_root).ask(parameters={THRESHOLD: 20}, as_of=before)

    assert result.temporal_boundary == before
    assert result.refused
    assert result.refusal is not None
    assert result.refusal.reason == "empty-operator-result"
    assert result.refusal.kind == "empty-result-refusal"

    served = _client(seeded_root).ask(parameters={THRESHOLD: 20}, as_of=_PINNED)
    assert not served.refused
    assert served.temporal_boundary == _PINNED
    assert served.payload["assembled"] == len(SEEDED_ROWS)


def test_reset_boot_cache_is_not_part_of_the_client_surface() -> None:
    """`D-03` fixes ``ccf.client`` at four names, and a test affordance is not one.

    A lifecycle control in a client developer's namespace to buy a test
    something the test can reach directly would be a fifth name that never
    stops being one.
    """
    import ccf.client

    assert "reset_boot_cache" not in ccf.client.__all__
    assert not hasattr(ccf.client, "reset_boot_cache")


def test_the_result_is_the_one_shape_every_transport_returns(
    seeded_root: Path,
) -> None:
    """`D-12`. The in-process leg goes through the same decoder as any wire."""
    result = _client(seeded_root).ask(parameters={THRESHOLD: 20})

    assert isinstance(result, Result)


def test_the_fixture_deployment_needs_no_credential_and_no_network(
    deployment_root: Path,
) -> None:
    """The always-on claim, asserted rather than described.

    A conformance suite that only runs when someone exports a DSN is an opt-in
    gate, and an opt-in parity gate protects nothing. So this asserts the
    property directly and **positively**: every setting the deployment's own
    ``connection:`` block composes to is a path *inside the deployment root*,
    which is a claim that cannot be satisfied by a host, a port or a credential.

    Stated as a property of the composed value rather than as "no environment
    variable is read", because the second is unobservable from here and the
    first is exactly what makes the suite runnable anywhere.

    ``D-IMPL-141``'s ruling made ``connection:`` **data** rather than a factory
    the loader imports and calls, so the composed mapping is read off the
    document. The property asserted is unchanged.
    """
    from ccf.client.adapters.binding_document import load_binding_document

    document = load_binding_document(deployment_root)
    composed = document.connection
    assert composed, "the fixture declares a connection and it composed to nothing"

    for setting, value in composed.items():
        resolved = Path(str(value)).resolve()
        assert document.root in resolved.parents, (
            f"connection setting `{setting}` is {value!r}, which is not a path"
            " inside the deployment root — this fixture must need no network"
            " and no credential"
        )
