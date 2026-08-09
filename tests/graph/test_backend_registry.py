"""The registration seam, pinned: discovery imports nothing, collisions refuse.

``ccf.graph.registry`` is the module the whole phase inverts around, and three
of its properties are the kind that read as true in a docstring and stop being
true without anything failing. Each gets an assertion here.

* **Discovery imports nothing** (D-05). The claim is not "we do not call
  ``.load()``" — that is a description of the code. The claim is that listing
  the adapters a deployment has installed does not execute an installed
  package's module-level body, and the only way to know that is to declare a
  module that records its own import and check it did not happen.
* **Both name collisions refuse, and refuse before anything loads.** Entry-point
  names are not deduplicated across distributions and the stdlib's mapping form
  answers with the first match silently. A registry that inherited that
  behaviour would resolve an adapter name to whichever package happened to be
  installed first, which is a deployment whose decisions cannot be reproduced.
* **The dynamic import is confined.** An AST import lint cannot see
  ``importlib.import_module``. The compensating control is that exactly one
  call site exists under ``src/`` and ``runtime/`` — and a compensating control
  is only worth the scan that proves it, so the scan covers the same two trees
  the rule it compensates for is scoped to.

Fakes rather than installed distributions, on purpose. The behaviours under
test are the *registry's decisions*; a test that needed ``pip install`` to run
is a test that does not run. The entry points here are real
:class:`importlib.metadata.EntryPoint` objects with a distribution attached
through the stdlib's own attachment path, so ``.name``, ``.value``,
``.dist.name`` and ``.dist.version`` read exactly as they do in production.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib.metadata as metadata
import pathlib
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from ccf.contracts.base import CCFContract
from ccf.graph import registry
from ccf.graph.registry import (
    BACKEND_ENTRY_POINT_GROUP,
    BackendRegistration,
    DuplicateBackendName,
    ReservedBackendName,
    UnknownBackend,
    declared_names,
    resolve,
)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The two trees ``RULE_TREE_SCOPE["backend-imports"]`` covers. The AST scans
#: below use exactly this pair — see their docstrings for why a narrower scan
#: would leave the accepted residual larger than the threat register says.
LINTED_TREES = ("src", "runtime")

#: A throwaway adapter. Its module-level body writes a marker file beside
#: itself, so "was this imported?" is answerable from disk as well as from
#: ``sys.modules``.
_PROBE_SOURCE = '''\
"""A throwaway adapter that records its own import."""

import pathlib

from ccf.contracts.base import CCFContract
from ccf.graph.registry import BackendRegistration

pathlib.Path(__file__).with_suffix(".imported").write_text("y", encoding="utf-8")


class ProbeConnection(CCFContract):
    endpoint: str


def _open_store(config, secrets):
    raise NotImplementedError


def _make_writer(store, token):
    raise NotImplementedError


REGISTRATION = BackendRegistration(
    name="ADAPTER_NAME",
    config_model=ProbeConnection,
    secret_fields=frozenset(),
    open_store=_open_store,
    make_writer=_make_writer,
)
'''


def _entry_point(
    *, name: str, value: str, distribution: str, version: str
) -> metadata.EntryPoint:
    """One declaration, with a distribution attached the stdlib's own way.

    ``EntryPoint._for`` is what :mod:`importlib.metadata` itself calls when it
    reads a real installed distribution, so a fake built this way answers
    ``.dist.name`` and ``.dist.version`` through the same attribute the registry
    reads in production rather than through a lookalike of its own.
    """
    point = metadata.EntryPoint(name, value, BACKEND_ENTRY_POINT_GROUP)
    return point._for(SimpleNamespace(name=distribution, version=version))


def _entry_points(*points: metadata.EntryPoint) -> metadata.EntryPoints:
    return metadata.EntryPoints(points)


@pytest.fixture
def probe_factory(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Any:
    """Write importable throwaway adapters and clean them out of the process.

    Every module this factory creates is removed from :data:`sys.modules` on
    teardown, because a module left behind would make the *next* test's
    "was it imported?" assertion pass for the wrong reason.
    """
    monkeypatch.syspath_prepend(str(tmp_path))
    created: list[str] = []

    def factory(module_name: str, adapter_name: str) -> pathlib.Path:
        source = _PROBE_SOURCE.replace("ADAPTER_NAME", adapter_name)
        path = tmp_path / f"{module_name}.py"
        path.write_text(source, encoding="utf-8")
        created.append(module_name)
        return path

    try:
        yield factory
    finally:
        for module_name in created:
            sys.modules.pop(module_name, None)


def _marker_of(module_path: pathlib.Path) -> pathlib.Path:
    return module_path.with_suffix(".imported")


def test_discovery_reads_names_without_importing_the_adapter(
    monkeypatch: pytest.MonkeyPatch, probe_factory: Any
) -> None:
    """V6 / D-05 — turning "discovery imports nothing" into a fact.

    The declared module records its own import in its module-level body. After
    ``declared_names()`` it is absent from ``sys.modules`` and its marker does
    not exist; after ``resolve()`` both are true. That is the difference between
    a property and a description of the code that is believed to have it.
    """
    module_name = "ccf_probe_discovery"
    module_path = probe_factory(module_name, "probe")
    monkeypatch.setattr(registry, "_builtin_names", dict)
    monkeypatch.setattr(
        registry,
        "_declared_entry_points",
        lambda: _entry_points(
            _entry_point(
                name="probe",
                value=f"{module_name}:REGISTRATION",
                distribution="ccf-probe-adapter",
                version="0.1.0",
            )
        ),
    )

    assert declared_names() == frozenset({"probe"})
    assert module_name not in sys.modules
    assert not _marker_of(module_path).exists()

    resolved = resolve("probe")

    assert module_name in sys.modules
    assert _marker_of(module_path).exists()
    assert resolved.registration.name == "probe"
    assert resolved.distribution == "ccf-probe-adapter"
    assert resolved.version == "0.1.0"


def test_declared_names_is_the_union_of_both_discovery_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-04's "both, not either", asserted rather than assumed.

    Built-ins come off the adapter package's directory and third parties come
    from entry-point metadata. A registry that read only one source would still
    pass every collision test below.
    """
    monkeypatch.setattr(
        registry, "_builtin_names", lambda: {"alpha": "pkg.alpha_write"}
    )
    monkeypatch.setattr(
        registry,
        "_declared_entry_points",
        lambda: _entry_points(
            _entry_point(
                name="omega",
                value="pkg.omega:REGISTRATION",
                distribution="ccf-omega-adapter",
                version="2.0.0",
            )
        ),
    )

    assert declared_names() == frozenset({"alpha", "omega"})


def test_an_unregistered_name_is_refused_with_what_is_registered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V9 — the refusal names what *is* available.

    The six-name ``Literal`` this replaces could only ever say what was
    hard-coded. The payback for removing it is a refusal that reads the
    deployment's actual adapter set back to the person who mistyped a name.
    """
    monkeypatch.setattr(
        registry,
        "_builtin_names",
        lambda: {"alpha": "pkg.alpha_write", "beta": "pkg.beta_write"},
    )
    monkeypatch.setattr(
        registry,
        "_declared_entry_points",
        lambda: _entry_points(
            _entry_point(
                name="omega",
                value="pkg.omega:REGISTRATION",
                distribution="ccf-omega-adapter",
                version="2.0.0",
            )
        ),
    )

    available = declared_names()
    with pytest.raises(UnknownBackend) as caught:
        resolve("alfa")

    message = str(caught.value)
    assert "alfa" in message
    for name in available:
        assert name in message, (name, message)
    assert BACKEND_ENTRY_POINT_GROUP in message


def test_a_duplicated_name_is_refused_naming_both_distributions(
    monkeypatch: pytest.MonkeyPatch, probe_factory: Any
) -> None:
    """V10 — and the companion assertion that makes it about the hazard.

    Two distributions declaring one name is refused in *discovery*, so
    ``resolve`` on the duplicated name loads neither candidate. Asserting only
    the exception would leave the test passing against a registry that refused
    after importing one of them, which is the failure that matters: by then a
    package nobody chose has already run its module-level code.
    """
    first_module = "ccf_probe_dup_first"
    second_module = "ccf_probe_dup_second"
    first_path = probe_factory(first_module, "dup")
    second_path = probe_factory(second_module, "dup")
    monkeypatch.setattr(registry, "_builtin_names", dict)
    monkeypatch.setattr(
        registry,
        "_declared_entry_points",
        lambda: _entry_points(
            _entry_point(
                name="dup",
                value=f"{first_module}:REGISTRATION",
                distribution="ccf-first-adapter",
                version="0.1.0",
            ),
            _entry_point(
                name="dup",
                value=f"{second_module}:REGISTRATION",
                distribution="ccf-second-adapter",
                version="9.9.9",
            ),
        ),
    )

    with pytest.raises(DuplicateBackendName) as caught:
        resolve("dup")

    message = str(caught.value)
    for token in ("ccf-first-adapter", "0.1.0", "ccf-second-adapter", "9.9.9"):
        assert token in message, (token, message)
    assert first_module not in sys.modules
    assert second_module not in sys.modules
    assert not _marker_of(first_path).exists()
    assert not _marker_of(second_path).exists()


def test_a_third_party_distribution_cannot_claim_a_builtin_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-16 — the SDK's own adapter names are reserved.

    The structural half is that built-ins never travel the entry-point path at
    all, so they cannot be shadowed. This refusal is the half that tells an
    operator *why* their installed package is being ignored, instead of leaving
    them to infer it from discovery order.
    """
    monkeypatch.setattr(
        registry, "_builtin_names", lambda: {"alpha": "pkg.alpha_write"}
    )
    monkeypatch.setattr(
        registry,
        "_declared_entry_points",
        lambda: _entry_points(
            _entry_point(
                name="alpha",
                value="pkg.impostor:REGISTRATION",
                distribution="ccf-impostor-adapter",
                version="9.9.9",
            )
        ),
    )

    with pytest.raises(ReservedBackendName) as caught:
        declared_names()

    message = str(caught.value)
    assert "ccf-impostor-adapter" in message
    assert "alpha" in message


@pytest.mark.parametrize(
    "declared",
    ["Alpha", "alpha.dotted", "1alpha", "alpha-dash", "ALPHA"],
)
def test_a_declared_name_of_the_wrong_shape_is_refused(
    monkeypatch: pytest.MonkeyPatch, declared: str
) -> None:
    """Exact match, lower case (D-16).

    A versioned document should not need a convention to say which case won,
    and a dotted name would be indistinguishable from an entry-point name that
    means something else. The refusal carries the offending value, because a
    name-shape complaint that does not show the name is unactionable.
    """
    monkeypatch.setattr(registry, "_builtin_names", dict)
    monkeypatch.setattr(
        registry,
        "_declared_entry_points",
        lambda: _entry_points(
            _entry_point(
                name=declared,
                value="pkg.thing:REGISTRATION",
                distribution="ccf-odd-adapter",
                version="0.0.1",
            )
        ),
    )

    with pytest.raises(ValueError) as caught:
        declared_names()

    assert declared in str(caught.value)


def test_a_builtin_discovered_but_not_registered_is_refused_by_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The window between the writer split and registration, as an assertion.

    Plan 15.4-03 creates the six write modules; plan 15.4-04 adds their
    registration records; they are separate waves. In between, built-in
    discovery finds adapters ``resolve`` cannot load, and the honest behaviour
    is a refusal that says which half is missing — never an ``AttributeError``
    escaping a ``getattr``, which tells the reader nothing about what to do.

    ``ccf.graph.protocols`` stands in for such a module: it imports cleanly and
    carries no registration record, which is exactly the shape being refused.
    """
    monkeypatch.setattr(
        registry, "_builtin_names", lambda: {"alpha": "ccf.graph.protocols"}
    )
    monkeypatch.setattr(registry, "_declared_entry_points", _entry_points)

    with pytest.raises(ValueError) as caught:
        resolve("alpha")

    assert not isinstance(caught.value, AttributeError)
    message = str(caught.value)
    assert "ccf.graph.protocols" in message
    assert "alpha" in message


def test_bad_metadata_from_an_unselected_adapter_refuses_every_boot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The fail-closed ruling, made a fact instead of a paragraph.

    ``resolve`` runs discovery first, so a reserved-name collision declared by
    a distribution that has nothing to do with the requested adapter refuses
    that boot too. **That is the ruling**, and it went this way because each of
    the three discovery refusals is evidence that the environment's answer to
    "which code does this name select" is ambiguous or wrong, and a fabric that
    boots past an ambiguity it cannot resolve has already decided something
    nobody asked it to decide.

    The narrower behaviour — degrade only the listing and the resolution of the
    offending name, leaving unrelated boots working — is recorded in the module
    docstring as considered and rejected. Anyone who wants it has to change a
    named decision, not delete an inconvenient assertion.

    The second half of this test is what keeps fail-closed operable: the
    refusal must read as a *packaging conflict*, not as a missing adapter, or
    the operator debugs the wrong thing.
    """
    monkeypatch.setattr(
        registry,
        "_builtin_names",
        lambda: {"alpha": "pkg.alpha_write", "beta": "pkg.beta_write"},
    )
    monkeypatch.setattr(
        registry,
        "_declared_entry_points",
        lambda: _entry_points(
            _entry_point(
                name="alpha",
                value="pkg.impostor:REGISTRATION",
                distribution="ccf-impostor-adapter",
                version="9.9.9",
            )
        ),
    )

    with pytest.raises(ReservedBackendName) as caught:
        resolve("beta")

    message = str(caught.value)
    assert "ccf-impostor-adapter" in message
    assert "packaging conflict" in message
    assert "no installed adapter registers" not in message


def test_a_registration_that_answers_to_another_name_is_refused(
    monkeypatch: pytest.MonkeyPatch, probe_factory: Any
) -> None:
    """T-15.4-14 — the loaded object must be the adapter it was resolved as.

    An entry point is metadata; the object behind it is code somebody else
    wrote. A record whose own name disagrees with the name it answered to is an
    adapter claiming to be another one, and the refusal names both so the
    disagreement is readable.
    """
    module_name = "ccf_probe_mismatch"
    probe_factory(module_name, "actual")
    monkeypatch.setattr(registry, "_builtin_names", dict)
    monkeypatch.setattr(
        registry,
        "_declared_entry_points",
        lambda: _entry_points(
            _entry_point(
                name="claimed",
                value=f"{module_name}:REGISTRATION",
                distribution="ccf-mismatch-adapter",
                version="0.1.0",
            )
        ),
    )

    with pytest.raises(ValueError) as caught:
        resolve("claimed")

    message = str(caught.value)
    assert "claimed" in message
    assert "actual" in message


def test_a_loaded_object_that_is_not_a_registration_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-15.4-14, the other half: an adapter registers a record, not a shape.

    ``resolve`` reads ``.name`` off whatever it loaded. Without the type check
    that read would be an ``AttributeError`` on a plausible-looking object, or
    worse, a silent success on one that happens to have a ``name``.
    """
    monkeypatch.setattr(registry, "_builtin_names", dict)
    monkeypatch.setattr(
        registry,
        "_declared_entry_points",
        lambda: _entry_points(
            _entry_point(
                name="notarecord",
                value="ccf.graph.protocols:GraphReader",
                distribution="ccf-notarecord-adapter",
                version="0.1.0",
            )
        ),
    )

    with pytest.raises(ValueError) as caught:
        resolve("notarecord")

    assert "BackendRegistration" in str(caught.value)


def _python_files() -> list[pathlib.Path]:
    return [
        path
        for tree in LINTED_TREES
        for path in sorted((_REPO_ROOT / tree).rglob("*.py"))
    ]


def _dynamic_import_sites(module: ast.Module) -> int:
    """Calls that reach :func:`importlib.import_module`, however spelled.

    Both spellings are counted and neither is double-counted:
    ``importlib.import_module(x)`` is one attribute access, and
    ``from importlib import import_module`` followed by ``import_module(x)`` is
    a call on a bare name.
    """
    count = 0
    for node in ast.walk(module):
        if isinstance(node, ast.Attribute) and node.attr == "import_module":
            count += 1
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "import_module"
        ):
            count += 1
    return count


def test_exactly_one_dynamic_import_site_exists_across_both_linted_trees() -> None:
    """T-15.4-03 — the compensating control, scanned at the threat's own width.

    ``cinv02-backend-import`` reads ``import`` statements and cannot see a
    dynamically-constructed module name. The residual is *accepted* on the
    strength of confinement, so the scan has to be at least as wide as the rule
    it compensates for: ``RULE_TREE_SCOPE["backend-imports"]`` is
    ``("src", "runtime")``, and a scan narrowed to the graph package would miss
    a dynamic ``import_module`` in the deployment wiring — which holds the
    adapter name and is exactly where someone would reach for one. A
    compensating control narrower than the threat is not a control.
    """
    sites = {
        path.relative_to(_REPO_ROOT).as_posix(): count
        for path in _python_files()
        if (
            count := _dynamic_import_sites(
                ast.parse(path.read_text(encoding="utf-8"))
            )
        )
    }

    assert sites == {"src/ccf/graph/registry.py": 1}, sites


def _make_writer_call_sites(module: ast.Module) -> int:
    """*Calls* of something named ``make_writer``.

    The field definition on ``BackendRegistration`` and its type annotation are
    not calls and are deliberately not counted: the question is who can obtain
    and invoke a writer constructor, not who can name the field that holds one.
    """
    count = 0
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        named = (isinstance(func, ast.Attribute) and func.attr == "make_writer") or (
            isinstance(func, ast.Name) and func.id == "make_writer"
        )
        if named:
            count += 1
    return count


def test_every_make_writer_call_site_is_the_composition_root() -> None:
    """T-15.4-43 — the one thing this seam made wider, stated and tested.

    ``BackendRegistration.make_writer`` is a public field on a public frozen
    dataclass returned by the public ``resolve``, and ``ccf.graph.registry`` is
    importable from anywhere. So after this phase a core module can obtain a
    writer constructor without importing a module ``cinv02-graph-writer``
    guards. The residual *mechanism* is unchanged — ``mint_boot_token`` stays in
    the guarded neutral base and still refuses a second live writer per graph
    identity — but D-01's argument is that the lint keeps its exact present
    shape, so the widening is asserted here rather than discovered later.
    """
    sites = {
        path.relative_to(_REPO_ROOT).as_posix(): count
        for path in _python_files()
        if (
            count := _make_writer_call_sites(
                ast.parse(path.read_text(encoding="utf-8"))
            )
        )
    }

    assert sorted(sites) == ["src/ccf/boot.py"], sites


def _unreachable(*args: object, **kwargs: object) -> Any:
    raise NotImplementedError


def test_the_registration_record_is_frozen() -> None:
    """A record the registry interprets cannot be edited after it is read.

    A mutable registration would let a caller swap ``make_writer`` on a record
    the registry already handed out, which is a write-handle constructor
    changing underneath the composition root.
    """
    record = BackendRegistration(
        name="alpha",
        config_model=CCFContract,
        secret_fields=frozenset(),
        open_store=_unreachable,
        make_writer=_unreachable,
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        record.name = "beta"
