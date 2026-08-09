"""The boot seam, pinned: lazy loading, the unknown-name refusal, the pin.

``tests/graph/test_backend_registry.py`` asserts these properties of
``ccf.graph.registry`` in isolation. This module asserts them **at boot** —
the seam an adopter actually meets — because the registry can be perfectly
well-behaved while the composition root above it undoes the property. Three
groups, each the boot-level form of a claim the registry makes:

* **V7 — only the named adapter is loaded.** Not "resolution imports one
  adapter", which is 15.4-04's assertion, but "a *complete* boot imports one
  adapter". This used to hold by two hand-written lazy branches inside
  ``ccf.boot``; it now holds by construction, and this is the test that says
  which of the two is true today.
* **V9 — an unregistered name is refused with what is registered.** Plus the
  case an adopter is far likelier to hit: a *misspelled* real name. That case
  is the payback D-12 names — a fixed six-name ``Literal`` could only ever say
  what was hard-coded, never what is installed.
* **The adapter pin.** ``FabricHandle.adapter`` names the adapter, its version,
  and the *reference names* the credentials came from — never the config
  fields they filled, and never a value.

**Subprocesses where the assertion needs one.** A ``sys.modules`` claim made
inside a session that has already imported six adapters proves nothing, so the
V7 tests run in a fresh interpreter and pass their evidence back as JSON.

The vocabulary is derived wherever it can be — the adapter set from
``declared_names()``, module paths from the registry's own package-and-suffix
convention, the optional-driver set from ``pyproject.toml`` — so a seventh
adapter joins these assertions on arrival. The one exception is
:data:`DEVELOPMENT_ADAPTER`, named once because a test that boots a fabric has
to boot *some* substrate and the shared fixture already knows how to fill this
one's connection contract. Every assertion around it is stated over the whole
derived set.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import SecretStr

from ccf.graph.registry import (
    BACKEND_ENTRY_POINT_GROUP,
    AdapterPin,
    ResolvedSecret,
    UnknownBackend,
    declared_names,
    resolve,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from ccf.boot import FabricHandle

#: The adapter this module boots for its positive cases: the one whose
#: connection contract the shared ``fabric_boot`` fixture already knows how to
#: fill, taken from the fixture's own default rather than named here.
DEVELOPMENT_ADAPTER = "sqlite"

#: A name of the required shape that no adapter can register, because the
#: registry refuses a declared name containing a dash. Kept distinct from the
#: misspelling case below: this one is "a name nobody could have", that one is
#: "a name somebody nearly typed".
UNREGISTERED_NAME = "not_an_adapter"


# --- V7: a complete boot loads exactly one adapter ---------------------------

#: Boot a fabric end to end in a fresh interpreter and report what got
#: imported. The Control Plane artifacts are built inline — values, so they
#: belong in a test rather than in ``/src`` (CLAUDE.md §11) — and the fabric is
#: closed before the report, so the graph is released and the report describes
#: a *completed* boot rather than a half-open one.
_BOOT_PROBE = '''\
import json
import pathlib
import sys
import tempfile

from ccf.assembly.worker import EntityResolutionRule, EntityResolutionSpec
from ccf.boot import boot
from ccf.controlplane.registry import ControlPlaneRegistry

adapter = sys.argv[1]
connection = json.loads(sys.argv[2])

registry = ControlPlaneRegistry()
spec_version = registry.register(
    "probe/spec",
    EntityResolutionSpec(
        semver="1.0.0",
        entity_rules=(
            EntityResolutionRule(
                match_key="probe_id",
                entity_class="probe",
                identity_keys=("probe_id",),
            ),
        ),
    ),
)
policy_version = registry.register("probe/policy", {"regime": "probe"})

with tempfile.TemporaryDirectory() as directory:
    resolved = {
        key: str(pathlib.Path(directory) / value) if key == "database_path" else value
        for key, value in connection.items()
    }
    handle = boot(
        backend=adapter,
        connection=resolved,
        registry=registry,
        resolution_spec_key="probe/spec",
        resolution_spec_version=spec_version,
        policy_bundle_key="probe/policy",
        policy_bundle_version=policy_version,
    )
    handle.close()

print(json.dumps(sorted(sys.modules)))
'''


def _modules_after_boot(adapter: str, connection: dict[str, Any]) -> frozenset[str]:
    """Everything a fresh interpreter imported while booting `adapter`."""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        entry for entry in sys.path if entry
    )
    completed = subprocess.run(
        [sys.executable, "-c", _BOOT_PROBE, adapter, json.dumps(connection)],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return frozenset(json.loads(completed.stdout))


def _write_module(adapter: str) -> str:
    """The dotted write-module path the registry derives for a built-in."""
    from ccf.graph.registry import BACKENDS_PACKAGE, WRITE_MODULE_SUFFIX

    return f"{BACKENDS_PACKAGE}.{adapter}{WRITE_MODULE_SUFFIX}"


def _adapter_write_modules(loaded: frozenset[str]) -> set[str]:
    from ccf.graph.registry import BACKENDS_PACKAGE, WRITE_MODULE_SUFFIX

    return {
        module
        for module in loaded
        if module.startswith(f"{BACKENDS_PACKAGE}.")
        and module.endswith(WRITE_MODULE_SUFFIX)
    }


def test_a_complete_boot_loads_no_other_adapters_write_module() -> None:
    """V7 at boot level: one adapter in, one adapter loaded.

    ``ccf.boot`` used to reach two of the six substrates through hand-written
    lazy ``import`` statements inside branches, with a comment explaining why.
    Both branches are gone and the property has to hold structurally now,
    because resolution imports exactly the write module a deployment named.

    Asserted over every adapter's write module rather than over two named
    drivers: the general form is what V7 is actually about, and a seventh
    adapter is covered on arrival.
    """
    loaded = _modules_after_boot(
        DEVELOPMENT_ADAPTER, {"database_path": "probe.sqlite3"}
    )
    # Non-vacuity: the subprocess really booted. An empty or truncated report
    # would satisfy every assertion below by asserting nothing.
    assert "ccf.boot" in loaded
    assert len(declared_names()) > 1, "one adapter installed proves nothing here"
    assert _adapter_write_modules(loaded) == {_write_module(DEVELOPMENT_ADAPTER)}


def test_a_complete_boot_loads_no_optional_driver() -> None:
    """V7, the driver form — the property the two lazy branches bought.

    The driver set is derived from the optional extras whose name is also a
    declared adapter name, mapped to the packages they install, so this module
    names no vendor. An adapter that moved its driver import to module top
    would fail here, which is the regression the deleted lazy branches used to
    guard against by hand.
    """
    drivers = _optional_driver_packages()
    assert drivers, "the derived driver set is empty — the derivation broke"
    loaded = _modules_after_boot(
        DEVELOPMENT_ADAPTER, {"database_path": "probe.sqlite3"}
    )
    assert "ccf.boot" in loaded
    assert not (drivers & loaded), sorted(drivers & loaded)


def _optional_driver_packages() -> frozenset[str]:
    """Import packages installed by the extras that name a declared adapter."""
    import importlib.metadata
    import pathlib
    import tomllib

    root = pathlib.Path(__file__).resolve().parents[2]
    with (root / "pyproject.toml").open("rb") as handle:
        extras = tomllib.load(handle)["project"]["optional-dependencies"]
    adapters = declared_names()
    distributions = importlib.metadata.packages_distributions()
    packages: set[str] = set()
    for extra, requirements in extras.items():
        if extra not in adapters:
            continue
        for requirement in requirements:
            name = (
                requirement.split(";")[0]
                .split("[")[0]
                .split("=")[0]
                .split(">")[0]
                .split("<")[0]
                .split("~")[0]
                .strip()
            )
            matched = {
                package
                for package, dists in distributions.items()
                if name in dists
            }
            packages |= matched or {name.replace("-", "_")}
    return frozenset(packages)


# --- V9: an unresolvable name is refused with what is registered -------------


def test_an_unregistered_name_is_refused_at_boot_naming_what_is_registered(
    banking_spec: Any,
) -> None:
    """V9 at boot level. The refusal is the registry's, reached through boot.

    ``boot`` resolves before it does anything else, so a name nothing registers
    fails before a Control Plane artifact is read, before a store is
    constructed, and before a token is minted.
    """
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    with pytest.raises(UnknownBackend) as caught:
        boot(
            backend=UNREGISTERED_NAME,
            registry=ControlPlaneRegistry(),
            resolution_spec_key="never",
            resolution_spec_version="never",
            policy_bundle_key="never",
            policy_bundle_version="never",
        )
    message = str(caught.value)
    assert UNREGISTERED_NAME in message
    for name in declared_names():
        assert name in message, f"{name} missing from {message!r}"
    assert BACKEND_ENTRY_POINT_GROUP in message


def test_a_misspelled_real_name_is_refused_the_same_way() -> None:
    """D-12's payback, in the case an adopter actually hits.

    A fixed ``Literal`` of six names could refuse a typo, but it could only ever
    list what was hard-coded — never what this deployment has installed, which
    is the answer a third-party adapter makes interesting. Same exception type,
    same message shape, and the list is the installed set.
    """
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    real = sorted(declared_names())[0]
    misspelled = f"{real}s"
    assert misspelled not in declared_names()

    with pytest.raises(UnknownBackend) as caught:
        boot(
            backend=misspelled,
            registry=ControlPlaneRegistry(),
            resolution_spec_key="never",
            resolution_spec_version="never",
            policy_bundle_key="never",
            policy_bundle_version="never",
        )
    message = str(caught.value)
    assert misspelled in message
    for name in declared_names():
        assert name in message
    assert BACKEND_ENTRY_POINT_GROUP in message


# --- the adapter pin ---------------------------------------------------------


def test_a_booted_handle_names_the_adapter_that_answered(
    fabric_boot: Callable[..., FabricHandle],
) -> None:
    """Whitepaper §7.10.1 dimension 2: which adapter, at which version.

    ``secret_refs`` is empty because this adapter declares no credential field,
    and an empty tuple is the honest answer rather than an absent one — the pin
    says "no reference was in force", which is a different fact from "the pin
    does not record references".
    """
    handle = fabric_boot()
    assert isinstance(handle.adapter, AdapterPin)
    assert handle.adapter.name == DEVELOPMENT_ADAPTER
    assert handle.adapter.name in declared_names()
    assert handle.adapter.version
    assert handle.adapter.secret_refs == ()


#: An adapter that declares a credential field and stores nothing durable. Its
#: store and writer are the SDK's own zero-dependency pair, so this probe tests
#: the *pin*, not a mock of one. Written to disk and declared through a fake
#: entry point, the pattern ``tests/graph/test_backend_registry.py`` sets.
_SECRETFUL_PROBE = '''\
"""A throwaway adapter that declares one credential field."""

from typing import Any

from ccf.contracts.base import CCFContract
from ccf.graph.backends.memory import MemoryGraphStore
from ccf.graph.backends.memory_write import MemoryGraphWriter
from ccf.graph.registry import BackendRegistration

SEEN: list[str] = []


class ProbeConnection(CCFContract):
    pass


def _open_store(config: Any, secrets: Any) -> Any:
    SEEN.append(secrets["CREDENTIAL_FIELD"].get_secret_value())
    return MemoryGraphStore()


def _make_writer(store: Any, token: Any) -> Any:
    return MemoryGraphWriter(store=store, token=token)


REGISTRATION = BackendRegistration(
    name="ADAPTER_NAME",
    config_model=ProbeConnection,
    secret_fields=frozenset({"CREDENTIAL_FIELD"}),
    open_store=_open_store,
    make_writer=_make_writer,
)
'''

#: The probe's credential field and the name of the reference it is resolved
#: from. Deliberately unalike: an assertion that accepted either would pass on
#: a pin that answers "a credential was used" where D-08 asks which one.
PROBE_CREDENTIAL_FIELD = "api_token"
PROBE_REFERENCE_NAME = "CCF_PROBE_TOKEN"
PROBE_SECRET_VALUE = "tok-do-not-log-me-9f3a"


@pytest.fixture
def secretful_adapter(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> Any:
    """Declare a credential-bearing adapter for the duration of one test."""
    import importlib.metadata as metadata
    from types import SimpleNamespace

    from ccf.graph import registry as registry_module

    adapter_name = "probe_secretful"
    module_name = "ccf_probe_secretful_write"
    source = _SECRETFUL_PROBE.replace("ADAPTER_NAME", adapter_name).replace(
        "CREDENTIAL_FIELD", PROBE_CREDENTIAL_FIELD
    )
    (tmp_path / f"{module_name}.py").write_text(source, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    point = metadata.EntryPoint(
        adapter_name, f"{module_name}:REGISTRATION", BACKEND_ENTRY_POINT_GROUP
    )
    point = point._for(SimpleNamespace(name="ccf-probe", version="9.9.9"))
    monkeypatch.setattr(
        registry_module,
        "_declared_entry_points",
        lambda: metadata.EntryPoints((point,)),
    )
    try:
        yield adapter_name
    finally:
        sys.modules.pop(module_name, None)


def test_the_pin_records_the_reference_name_never_the_field_or_the_value(
    secretful_adapter: str, banking_spec: Any
) -> None:
    """D-08/D-09: which reference was in force, answerable from the pin alone.

    Two assertions that have to be made together. The reference name is
    present, and the *field* name is absent — a pin built from the ``secrets``
    mapping's keys would say a ``{field}`` was supplied and could never say
    which reference supplied it, which is the fact D-08 exists to make
    auditable.

    The third assertion is the credential's absence from every rendering the
    pin has. This is V13's precondition: whatever else records an adapter pin
    downstream, it cannot record a credential, because the pin has no field
    that could hold one.
    """
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    registry = ControlPlaneRegistry()
    spec_version = registry.register("probe/spec", banking_spec)
    policy_version = registry.register("probe/policy", {"regime": "probe"})

    handle = boot(
        backend=secretful_adapter,
        secrets={
            PROBE_CREDENTIAL_FIELD: ResolvedSecret(
                field=PROBE_CREDENTIAL_FIELD,
                ref_name=PROBE_REFERENCE_NAME,
                value=SecretStr(PROBE_SECRET_VALUE),
            )
        },
        registry=registry,
        resolution_spec_key="probe/spec",
        resolution_spec_version=spec_version,
        policy_bundle_key="probe/policy",
        policy_bundle_version=policy_version,
    )
    try:
        pin = handle.adapter
        assert pin.name == secretful_adapter
        assert pin.version == "9.9.9"
        assert pin.secret_refs == (PROBE_REFERENCE_NAME,)
        assert PROBE_CREDENTIAL_FIELD not in pin.secret_refs

        for rendering in (repr(pin), str(pin), pin.model_dump_json()):
            assert PROBE_SECRET_VALUE not in rendering

        # Non-vacuity: the value really did reach the adapter, so its absence
        # from the pin is a property of the pin rather than of the boot.
        probe = sys.modules["ccf_probe_secretful_write"]
        assert probe.SEEN == [PROBE_SECRET_VALUE]
    finally:
        handle.close()


def test_the_adapter_version_is_the_declaring_distributions(
    secretful_adapter: str,
) -> None:
    """The pin's version is derived, never declared by the adapter.

    A third-party adapter gets its replay pin from its own distribution's
    metadata and cannot mis-state it — the record it registers carries no
    version field at all.
    """
    resolved = resolve(secretful_adapter)
    assert resolved.version == "9.9.9"
    assert resolved.distribution == "ccf-probe"
    assert not hasattr(resolved.registration, "version")


# --- a boot that fails leaves nothing behind (CR-01) -------------------------

#: An adapter whose writer constructor raises on demand, over a store whose
#: graph identity is supplied rather than generated. Both properties are
#: needed: the raise is the third-party failure being reproduced, and the fixed
#: identity is what lets a *second* boot collide with the first if the first
#: left the graph marked as written-to.
_EXPLODING_WRITER_PROBE = '''\
"""A throwaway adapter whose writer constructor can be made to raise."""

from typing import Any

from ccf.contracts.base import CCFContract
from ccf.graph.backends.memory import MemoryGraphStore
from ccf.graph.backends.memory_write import MemoryGraphWriter
from ccf.graph.registry import BackendRegistration

#: Flipped by the test between the failing boot and the corrected retry.
EXPLODE = [True]

#: Every store this adapter opened, in order. Each counts its own closes, so
#: "was the store released?" is answerable from the test rather than inferred.
OPENED: list[Any] = []


class ProbeConnection(CCFContract):
    identity: str


class _FixedIdentityStore(MemoryGraphStore):
    """The in-memory store with its identity supplied instead of generated.

    A subclass rather than a wrapper so the adapter's own writer constructor
    still sees the type it writes through.
    """

    def __init__(self, identity: str) -> None:
        super().__init__()
        self._graph_identity = identity
        self.closes = 0

    def close(self) -> None:
        self.closes += 1
        super().close()


def _open_store(config: Any, secrets: Any) -> Any:
    store = _FixedIdentityStore(config.identity)
    OPENED.append(store)
    return store


def _make_writer(store: Any, token: Any) -> Any:
    if EXPLODE[0]:
        raise RuntimeError("third-party adapter blew up building its writer")
    return MemoryGraphWriter(store=store, token=token)


REGISTRATION = BackendRegistration(
    name="ADAPTER_NAME",
    config_model=ProbeConnection,
    secret_fields=frozenset(),
    open_store=_open_store,
    make_writer=_make_writer,
)
'''


@pytest.fixture
def exploding_writer_adapter(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Declare the failing-writer adapter for the duration of one test."""
    import importlib.metadata as metadata
    from types import SimpleNamespace

    from ccf.graph import registry as registry_module

    adapter_name = "probe_exploding"
    module_name = "ccf_probe_exploding_write"
    source = _EXPLODING_WRITER_PROBE.replace("ADAPTER_NAME", adapter_name)
    (tmp_path / f"{module_name}.py").write_text(source, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    point = metadata.EntryPoint(
        adapter_name, f"{module_name}:REGISTRATION", BACKEND_ENTRY_POINT_GROUP
    )
    point = point._for(SimpleNamespace(name="ccf-probe", version="9.9.9"))
    monkeypatch.setattr(
        registry_module,
        "_declared_entry_points",
        lambda: metadata.EntryPoints((point,)),
    )
    try:
        yield adapter_name, module_name
    finally:
        sys.modules.pop(module_name, None)


def test_a_failing_writer_constructor_closes_the_store_and_frees_the_graph(
    exploding_writer_adapter: Any, banking_spec: Any
) -> None:
    """CR-01 — the guard around the one call the composition root does not own.

    ``mint_boot_token`` marks a graph as written-to and only a writer's
    ``close`` ever unmarks it, so the window between the mint and the writer is
    the one place a failure can leave a graph permanently unbootable. Since
    D-IMPL-93 that window contains third-party code.

    Three assertions, and each fails without the guard:

    * the adapter's exception reaches the caller unchanged, so nothing is
      swallowed or re-typed on the way out;
    * the store this boot opened was closed, so the connection it holds — a
      driver client in every real adapter — is not leaked to a caller who was
      handed no object to close it with;
    * **a corrected retry over the same graph boots.** That is the one
      ``ccf.boot`` states as the thing that must not happen, and it is what
      makes this a fabric-level defect rather than a leak: the operator fixes
      the adapter, restarts nothing, and the fabric refuses them anyway.
    """
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    adapter_name, module_name = exploding_writer_adapter
    identity = "probe://cr-01-one-graph"
    control_plane = ControlPlaneRegistry()
    spec_version = control_plane.register("probe/spec", banking_spec)
    policy_version = control_plane.register("probe/policy", {"regime": "probe"})

    def _boot() -> Any:
        return boot(
            backend=adapter_name,
            connection={"identity": identity},
            registry=control_plane,
            resolution_spec_key="probe/spec",
            resolution_spec_version=spec_version,
            policy_bundle_key="probe/policy",
            policy_bundle_version=policy_version,
        )

    with pytest.raises(RuntimeError) as caught:
        _boot()
    assert "blew up building its writer" in str(caught.value)

    probe = sys.modules[module_name]
    assert len(probe.OPENED) == 1
    assert probe.OPENED[0].closes == 1

    probe.EXPLODE[0] = False
    handle = _boot()
    try:
        assert handle.adapter.name == adapter_name
    finally:
        handle.close()
