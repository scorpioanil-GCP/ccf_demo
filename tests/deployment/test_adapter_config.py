"""V7 / V11 / V12 — what every registered adapter refuses, and what resolving
one loads.

Plan 15.4-04, D-07. Before this phase, "which connection argument does this
backend require" was a hand-maintained mapping in
``ccf.deployment.manifest._preflight_backend`` and two refusals were written
against it: a declared backend whose connection argument is missing is refused,
and an argument the declared backend does not take is refused rather than
ignored. Both had to survive the move into the adapters. This module is where
they are asserted, **per adapter**.

Every parameter list here is built from
:func:`ccf.graph.registry.declared_names`, never written out. That is not
tidiness: a hand-written list of six names in a test file is the same defect
this phase removes from ``src/`` — the thing that has to be edited when a
seventh substrate arrives, and the thing that is silently wrong until somebody
remembers. Derived, a seventh adapter is covered on arrival for the same reason
it becomes discoverable on arrival.

Why the ``extra="forbid"`` sweep is the load-bearing test
--------------------------------------------------------

Of the two refusals, the undeclared-key one is the one a migration loses
silently. It used to be an explicit loop over every *other* backend's
connection argument. Now it comes entirely from the ``extra="forbid"`` a config
model inherits from :class:`~ccf.contracts.base.CCFContract`. A model written
against a plain open base still accepts every valid manifest, so nothing else
in the suite would go red — the warning sign would be a manifest with a typo'd
connection key booting successfully, in somebody's deployment, months later.

Where the refusal message is built, and where it is not
-------------------------------------------------------

The V11 assertions go through :func:`ccf.graph.registry.validate_connection`
**by name**. That function is the single owner of connection-refusal text, and
the reason it has a single owner is that a refusal formatted from a
``ValidationError``'s own rendering embeds the value that was supplied — and
one of those values is a credential. A second formatter written here, in a test
that exists to assert the property, would be the first crack in it. So this
module builds no message of its own: it asserts what the wrapper produced.

The credential assertion is per adapter on purpose
--------------------------------------------------

``tests/graph/test_backend_registry.py`` already asserts that a supplied value
cannot travel with a refusal, against a fixture registration. This module
asserts it against every **real** adapter, because that is where an adopter
meets it and where the one credential-bearing adapter's token actually travels.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tomllib

import pytest
from pydantic import ValidationError

from ccf.graph.registry import (
    BACKENDS_PACKAGE,
    WRITE_MODULE_SUFFIX,
    BackendRegistration,
    InvalidBackendConfig,
    declared_names,
    resolve,
    validate_connection,
)

#: Every adapter this deployment has installed, read from the registry rather
#: than listed. Computed once at import: a packaging conflict refuses discovery
#: outright, and a collection error is the honest report of that.
ADAPTER_NAMES: list[str] = sorted(declared_names())

#: A settings key no adapter declares. One fixed nonsense token rather than a
#: per-adapter guess, so the assertion is about the contract base and not about
#: any adapter's field list.
UNDECLARED_KEY = "not_a_setting"

#: A recognisable value supplied under :data:`UNDECLARED_KEY`. It stands in for
#: the case that actually happens: an adopter misspells a connection key and the
#: value beside it was meant for somewhere else — which, for one adapter, is a
#: live credential.
RECOGNISABLE_VALUE = "ccf-adapter-config-do-not-log-me-4b17"

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"

#: Run in a **fresh interpreter** and print what it loaded. In-process the
#: assertion would be about whatever the test session already imported, which is
#: not the claim: the claim is about a boot.
_PROBE = (
    "import json, sys\n"
    "import ccf.graph.registry as registry\n"
    "registry.resolve(sys.argv[1])\n"
    "json.dump(sorted(sys.modules), sys.stdout)\n"
)


def _write_module(adapter: str) -> str:
    """The dotted write module a built-in adapter's record lives in.

    The package and the suffix are read from the registry, so the convention has
    one definition and this module is not a second one.
    """
    return f"{BACKENDS_PACKAGE}.{adapter}{WRITE_MODULE_SUFFIX}"


def _is_builtin(adapter: str) -> bool:
    """Whether `adapter` ships here, as opposed to arriving through an entry point."""
    return importlib.util.find_spec(_write_module(adapter)) is not None


def _optional_driver_packages() -> frozenset[str]:
    """Import names of the drivers that are only available through an extra.

    Derived, not listed. An optional extra whose name is also a declared adapter
    name *is* that adapter's driver requirement — that correspondence is real
    and is what makes "the driver is an optional extra" a checkable statement
    rather than a comment. Distribution names are mapped to the packages they
    actually install where the distribution is present, and fall back to the
    normalized distribution name where it is not, so the derivation works in an
    extras-free environment as well as in a full one.
    """
    document = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    extras = document["project"]["optional-dependencies"]
    installed: dict[str, set[str]] = {}
    for package, distributions in importlib.metadata.packages_distributions().items():
        for distribution in distributions:
            key = distribution.lower().replace("-", "_")
            installed.setdefault(key, set()).add(package)

    packages: set[str] = set()
    for adapter in ADAPTER_NAMES:
        for requirement in extras.get(adapter, ()):
            # Strip the version pin, any extras bracket, and any environment
            # marker — what remains is the distribution name.
            distribution = (
                requirement.split(";")[0]
                .split("[")[0]
                .split("==")[0]
                .split(">=")[0]
                .split("<")[0]
                .strip()
                .lower()
                .replace("-", "_")
            )
            packages |= installed.get(distribution, {distribution})
    return frozenset(packages)


#: Computed once — see :func:`_optional_driver_packages`.
OPTIONAL_DRIVER_PACKAGES: frozenset[str] = _optional_driver_packages()


def _loaded_modules(adapter: str) -> frozenset[str]:
    """What a fresh interpreter has imported after resolving `adapter`."""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        entry for entry in sys.path if entry
    )
    completed = subprocess.run(
        [sys.executable, "-c", _PROBE, adapter],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    loaded: list[str] = json.loads(completed.stdout)
    return frozenset(loaded)


# --- non-vacuity ------------------------------------------------------------


def test_the_derived_adapter_list_is_not_vacuous() -> None:
    """A parameterisation over an empty list passes by testing nothing.

    Every test below is parameterised from the registry, which is the point —
    and is also how the whole module could go green while asserting nothing at
    all. This is the leg that says otherwise.
    """
    assert ADAPTER_NAMES
    for adapter in ADAPTER_NAMES:
        registration = resolve(adapter).registration
        assert isinstance(registration, BackendRegistration)
        assert registration.name == adapter


def test_the_optional_driver_set_is_not_vacuous() -> None:
    """The derived driver set must actually name drivers.

    :func:`_optional_driver_packages` reads ``pyproject.toml`` and could return
    the empty set after a rename — at which point the absence assertions below
    would pass against a tree that loads every driver at resolution.
    """
    assert OPTIONAL_DRIVER_PACKAGES


# --- V12: the sweep, and the per-adapter undeclared-key refusal --------------


@pytest.mark.parametrize("adapter", ADAPTER_NAMES)
def test_every_config_model_is_closed_and_frozen(adapter: str) -> None:
    """V12. The whole of one surviving refusal is this configuration.

    Pitfall 1: a config model written against a plain open base gets Pydantic's
    ``extra="ignore"`` default, keeps every valid manifest working, and loses
    the "an argument the declared backend does not take is refused" guarantee
    with nothing going red. ``frozen`` is asserted alongside it because both
    come from the same inheritance, and a model that lost one probably lost the
    other.
    """
    model = resolve(adapter).registration.config_model
    assert model.model_config["extra"] == "forbid", adapter
    assert model.model_config["frozen"] is True, adapter


@pytest.mark.parametrize("adapter", ADAPTER_NAMES)
def test_an_undeclared_setting_is_refused_naming_the_key(adapter: str) -> None:
    """V12, per adapter: refused, not ignored, and the key is named.

    Asserted on the error's own type rather than on message text, because
    ``extra_forbidden`` is the specific thing that must fire — a ``missing``
    error for some unrelated required field would otherwise let this pass
    against a model that ignores extras.
    """
    model = resolve(adapter).registration.config_model
    with pytest.raises(ValidationError) as caught:
        model.model_validate({UNDECLARED_KEY: RECOGNISABLE_VALUE})

    details = caught.value.errors()
    extras = [detail for detail in details if detail["type"] == "extra_forbidden"]
    assert extras, details
    assert any(UNDECLARED_KEY in detail["loc"] for detail in extras), details
    assert UNDECLARED_KEY in str(caught.value)


# --- V11: the missing required setting, through the one wrapper -------------


def _required_fields(registration: BackendRegistration) -> list[str]:
    """The settings an adapter cannot be constructed without."""
    return sorted(
        name
        for name, field in registration.config_model.model_fields.items()
        if field.is_required()
    )


@pytest.mark.parametrize("adapter", ADAPTER_NAMES)
def test_a_missing_required_setting_is_refused_naming_adapter_and_field(
    adapter: str,
) -> None:
    """V11, per adapter, through :func:`validate_connection` by name.

    Two halves, and the second is the one the migration could have lost.
    Pydantic reports the *model class* and the field; the check this replaces
    reported the **adapter** and the field. A caller reading "1 validation error
    for PostgresConnection" has to know which adapter that class belongs to,
    which is exactly the knowledge the registry exists so nobody needs.

    The wrapper is called by name rather than reimplemented here: it is the
    single owner of connection-refusal text, and it has a single owner because
    a refusal formatted from a ``ValidationError``'s own rendering carries the
    value that was supplied.

    An adapter with no required settings asserts the other half of the same
    contract rather than being skipped: an empty mapping *validates*. That is
    the zero-dependency adapter's actual guarantee — the one special-cased entry
    the old mapping carried, restated as a property that every future adapter
    with no required settings inherits — and a skipped row would leave it
    unasserted.
    """
    registration = resolve(adapter).registration
    required = _required_fields(registration)
    if not required:
        validated = validate_connection(registration, {})
        assert isinstance(validated, registration.config_model)
        return

    with pytest.raises(ValidationError) as raw:
        registration.config_model.model_validate({})
    details = raw.value.errors()
    missing = [detail for detail in details if detail["type"] == "missing"]
    assert missing, details
    located = {str(part) for detail in missing for part in detail["loc"]}
    assert set(required) <= located, (required, located)

    with pytest.raises(InvalidBackendConfig) as caught:
        validate_connection(registration, {})
    message = str(caught.value)
    assert adapter in message, message
    for field in required:
        assert field in message, (field, message)


@pytest.mark.parametrize("adapter", ADAPTER_NAMES)
def test_a_value_under_an_undeclared_key_reaches_no_part_of_the_exception(
    adapter: str,
) -> None:
    """V13b, per adapter — the hazard, not the happy path.

    A misspelled connection key is precisely the case where a value lands under
    a name nobody declared, and for one of these adapters that value is a
    credential. Pydantic embeds ``input_value=`` verbatim, so the supplied value
    is one string interpolation away from every log and every traceback.

    The chain is asserted as well as the text: ``raise ... from None`` would
    suppress the *printed* chain and leave the ``ValidationError`` reachable on
    ``__context__``, where a structured logger or an error reporter would find
    it.
    """
    registration = resolve(adapter).registration
    with pytest.raises(InvalidBackendConfig) as caught:
        validate_connection(
            registration, {UNDECLARED_KEY: RECOGNISABLE_VALUE}
        )

    assert RECOGNISABLE_VALUE not in str(caught.value)
    assert RECOGNISABLE_VALUE not in repr(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    # And the refusal is still useful: it names the adapter and the key.
    assert adapter in str(caught.value)
    assert UNDECLARED_KEY in str(caught.value)


# --- V7: resolving one adapter loads that adapter and nothing else ----------


@pytest.mark.parametrize("adapter", ADAPTER_NAMES)
def test_resolving_one_adapter_loads_no_other_adapters_write_module(
    adapter: str,
) -> None:
    """V7, the general form: selection imports exactly what was selected.

    Asserted in a subprocess so the fact is about a fresh interpreter rather
    than about whatever the test session already pulled in. The expected set is
    derived from the registry's own package-and-suffix convention, so a seventh
    adapter joins this assertion on arrival.

    This is what ``ccf.boot._open_backend`` achieved with hand-written lazy
    import branches, one per optional-extra substrate. After this phase it holds
    by construction, and this is the test that makes that a fact rather than a
    claim.
    """
    loaded = _loaded_modules(adapter)
    write_modules = {
        module
        for module in loaded
        if module.startswith(f"{BACKENDS_PACKAGE}.")
        and module.endswith(WRITE_MODULE_SUFFIX)
    }
    expected = {_write_module(adapter)} if _is_builtin(adapter) else set()
    assert write_modules == expected, sorted(write_modules)


@pytest.mark.parametrize("adapter", ADAPTER_NAMES)
def test_resolving_any_adapter_loads_no_optional_driver(adapter: str) -> None:
    """V7, the driver form: no extra's package is imported at resolution.

    Stronger than "resolving the development adapter loads no driver", and
    deliberately so. It holds for **every** adapter, including the ones whose
    own substrate needs an optional extra, because a driver import lives inside
    its store constructor and resolution constructs no store. An adapter that
    moved its driver import to module top would fail here on its own row.

    The driver set is derived from ``pyproject.toml`` (see
    :func:`_optional_driver_packages`) rather than listed, so this module names
    no substrate and no vendor, and a seventh adapter arriving with a seventh
    extra is covered by the same derivation.
    """
    loaded = _loaded_modules(adapter)
    assert not (loaded & OPTIONAL_DRIVER_PACKAGES), sorted(
        loaded & OPTIONAL_DRIVER_PACKAGES
    )
