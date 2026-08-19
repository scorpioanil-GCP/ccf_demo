"""Binding resolution — three steps, no fourth, and precedence proven by dispatch.

``D-05``, ``D-06``, ``D-21``. The resolution is deliberately minimal: an
explicit ``binding=`` kwarg, else ``CCF_BINDING``, else a ``BindingError``
naming exactly what to set. There is no bindings file, no per-product env-var
naming and no discovery chain, because *the resolution chain is how 722-line
examples happen* (spec §3).

Why the precedence test observes dispatch
------------------------------------------
``17-RESEARCH.md`` §7, the ``D-21`` row: *"assert the kwarg wins by observing
which adapter ran, not by reading back a stored attribute — a stored attribute
proves storage, not dispatch."* So the tests here register two fake schemes and
assert on **which factory was invoked with which address**. A client that stored
the right binding and then dispatched on the other one would pass the stored
form of this test and fail this one.
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping
from typing import Final

import pytest

from ccf.client.binding import (
    BINDING_ENV_VAR,
    SCHEME_REGISTRY,
    adapter_for_binding,
    resolve_binding,
    split_binding,
)
from ccf.client.errors import BindingError, TransportError
from ccf.client.wire import WireOutcome, WireRequest

_BINDING_SOURCE: Final = (
    pathlib.Path(__file__).resolve().parents[2] / "src" / "ccf" / "client" / "binding.py"
)


# --------------------------------------------------------------------------
# Two fake transports, so precedence can be observed as dispatch
# --------------------------------------------------------------------------


class _RecordingAdapter:
    """A transport that records the address its factory was handed."""

    def __init__(self, scheme: str, address: str, log: list[tuple[str, str]]) -> None:
        self.scheme = scheme
        self.address = address
        log.append((scheme, address))

    def ask(self, request: WireRequest) -> WireOutcome:  # pragma: no cover
        raise NotImplementedError("this fake never speaks; it only records")


@pytest.fixture
def dispatch_log(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Register two fake schemes for the duration of one test.

    ``monkeypatch.setitem`` rather than a replacement dict, so the tests
    exercise the **shipped** registry object and the shipped lookup rather than
    a parallel one that could diverge. Removal is automatic at teardown.
    """
    log: list[tuple[str, str]] = []

    def factory(scheme: str) -> object:
        def build(address: str) -> _RecordingAdapter:
            return _RecordingAdapter(scheme, address, log)

        return build

    monkeypatch.setitem(SCHEME_REGISTRY, "fake-a", factory("fake-a"))  # type: ignore[arg-type]
    monkeypatch.setitem(SCHEME_REGISTRY, "fake-b", factory("fake-b"))  # type: ignore[arg-type]
    return log


# --------------------------------------------------------------------------
# Behaviour 1 — the kwarg wins, observed as dispatch
# --------------------------------------------------------------------------


def test_an_explicit_kwarg_beats_a_set_env_var(
    dispatch_log: list[tuple[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(BINDING_ENV_VAR, "fake-b:from-the-environment")

    adapter_for_binding("fake-a:from-the-kwarg")

    assert dispatch_log == [("fake-a", "from-the-kwarg")], (
        "the kwarg must decide which adapter is built and what address it is"
        f" built with; dispatch went to {dispatch_log}"
    )


# --------------------------------------------------------------------------
# Behaviour 2 — the env var is step two
# --------------------------------------------------------------------------


def test_the_env_var_is_used_when_no_kwarg_is_given(
    dispatch_log: list[tuple[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(BINDING_ENV_VAR, "fake-b:from-the-environment")

    adapter_for_binding()

    assert dispatch_log == [("fake-b", "from-the-environment")]


# --------------------------------------------------------------------------
# Behaviour 3 — neither, and the message names what to set
# --------------------------------------------------------------------------


def test_neither_a_kwarg_nor_an_env_var_raises_binding_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(BINDING_ENV_VAR, raising=False)

    with pytest.raises(BindingError) as raised:
        resolve_binding()

    message = str(raised.value)
    assert "CCF_BINDING" in message, (
        "the message must name the variable literally — a refusal that says"
        f" *something* is unset is not a refusal-quality one: {message!r}"
    )
    assert "for_product" in message, (
        "the message must also name the other way to supply it, so a reader"
        f" learns both steps from the failure: {message!r}"
    )


def test_a_blank_env_var_is_treated_as_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``CCF_BINDING=""`` says nothing, so it must not be dispatched on.

    Passing a blank address through would reach the scheme split and refuse
    there with a message about a missing scheme prefix — which names the wrong
    problem to whoever exported an empty variable.
    """
    monkeypatch.setenv(BINDING_ENV_VAR, "   ")

    with pytest.raises(BindingError, match="CCF_BINDING"):
        resolve_binding()


# --------------------------------------------------------------------------
# Behaviour 4 — an unregistered scheme names the ones that are registered
# --------------------------------------------------------------------------


def test_an_unregistered_scheme_names_the_registered_ones(
    dispatch_log: list[tuple[str, str]],
) -> None:
    with pytest.raises(BindingError) as raised:
        adapter_for_binding("carrier-pigeon:./deployment")

    message = str(raised.value)
    assert "carrier-pigeon" in message, "the message must name the scheme that failed"
    assert "fake-a" in message and "fake-b" in message, (
        f"the message must name the schemes that are registered: {message!r}"
    )
    assert not dispatch_log, "nothing may be built for a scheme nobody registered"


def test_an_unregistered_scheme_refuses_loudly_on_an_empty_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty registry must refuse, not fall through to a default.

    This is the fail-open case, and it is the one worth writing down: a lookup
    that quietly does nothing when it can resolve nothing is a gate that goes
    silent exactly when the deployment is least configured. The registry is
    empty until an adapter plan registers a scheme, so the empty case is real
    today rather than hypothetical.
    """
    monkeypatch.setattr("ccf.client.binding.SCHEME_REGISTRY", {})

    with pytest.raises(BindingError) as raised:
        adapter_for_binding("inprocess:./deployment")

    assert "no transport scheme" in str(raised.value).lower()


# --------------------------------------------------------------------------
# Behaviour 5 — an address with no scheme prefix
# --------------------------------------------------------------------------


def test_an_address_with_no_scheme_prefix_raises_binding_error() -> None:
    with pytest.raises(BindingError) as raised:
        adapter_for_binding("./deployment")

    message = str(raised.value)
    assert "scheme" in message.lower()
    assert "inprocess:" in message, (
        f"the message must show the shape it wanted, not merely name it: {message!r}"
    )


@pytest.mark.parametrize(
    "malformed",
    [
        pytest.param("./deployment", id="no-colon"),
        pytest.param(":./deployment", id="empty-scheme"),
        pytest.param("inprocess:", id="empty-address"),
        pytest.param("inprocess:   ", id="blank-address"),
    ],
)
def test_every_malformed_shape_is_refused(malformed: str) -> None:
    """Four ways to be malformed, each refused rather than half-resolved."""
    with pytest.raises(BindingError):
        split_binding(malformed)


def test_a_url_shaped_binding_splits_on_the_first_colon_only() -> None:
    """``http://host/path`` must not lose its own separators to the split."""
    assert split_binding("http://host/path") == ("http", "//host/path")


def test_a_compound_scheme_survives_the_split() -> None:
    """``mcp+stdio`` is one scheme name, not two."""
    assert split_binding("mcp+stdio:./deployment") == ("mcp+stdio", "./deployment")


# --------------------------------------------------------------------------
# Behaviour 6 — one catch-all for "the wire never spoke"
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda: resolve_binding(), id="missing-binding"),
        pytest.param(
            lambda: adapter_for_binding("carrier-pigeon:x"), id="unknown-scheme"
        ),
        pytest.param(lambda: adapter_for_binding("./deployment"), id="no-scheme"),
    ],
)
def test_every_binding_failure_is_caught_by_the_transport_clause(
    call: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``D-10``: a caller does not have to know *which* way it failed."""
    monkeypatch.delenv(BINDING_ENV_VAR, raising=False)

    with pytest.raises(TransportError):
        call()  # type: ignore[operator]


# --------------------------------------------------------------------------
# D-05's "no fourth step" — asserted against the source, and loudly
# --------------------------------------------------------------------------


def source_of(path: pathlib.Path) -> str:
    """Read a module's source, refusing to pass when it cannot be read.

    A scan that skips what it cannot resolve is a gate that goes quiet exactly
    when the tree gets complicated. So this raises on a missing file rather
    than returning an empty string that every ``not in`` assertion below would
    then satisfy.
    """
    if not path.is_file():
        raise AssertionError(
            f"{path} is not a readable file, so the no-fourth-step assertion"
            " would pass over nothing at all"
        )
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "mechanism",
    ["entry_point", "entry_points", "importlib.metadata", "register_scheme"],
)
def test_no_plugin_mechanism_is_built(mechanism: str) -> None:
    """``D-05``/``D-06``: third-party schemes wait for someone real to ask.

    An entry-point lookup, a registration decorator or a metadata scan is each
    a fourth resolution step wearing a different hat, and each one puts the
    answer to *where does this client talk to* somewhere the reader of
    ``consume.py`` cannot see.
    """
    assert mechanism not in source_of(_BINDING_SOURCE)


def test_the_no_fourth_step_scan_reads_a_populated_source() -> None:
    """The control for the scan above: it must be reading something real."""
    assert len(source_of(_BINDING_SOURCE)) > 500


def test_control_the_source_scan_refuses_a_path_it_cannot_resolve(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL — the scan fails loudly on an unresolvable subject.

    Without this, moving or renaming ``binding.py`` would turn every
    ``mechanism not in ""`` assertion above green forever, which is precisely
    the failing-open shape that let a citation gate pass vacuously for a full
    wave of this phase.
    """
    with pytest.raises(AssertionError, match="not a readable file"):
        source_of(tmp_path / "there-is-no-such-module.py")


# --------------------------------------------------------------------------
# The registry is a plain dict, and that is the whole extension story
# --------------------------------------------------------------------------


def test_the_registry_is_a_plain_mutable_mapping() -> None:
    assert isinstance(SCHEME_REGISTRY, dict)


def test_a_registered_scheme_is_dispatched_to_with_its_address_only(
    dispatch_log: list[tuple[str, str]],
) -> None:
    """The factory receives the remainder, never the scheme prefix again."""
    adapter = adapter_for_binding("fake-a:./deployment")

    assert isinstance(adapter, _RecordingAdapter)
    assert adapter.address == "./deployment"
    assert dispatch_log == [("fake-a", "./deployment")]


def test_resolution_reads_an_injected_environment_when_one_is_given() -> None:
    """The environment is a parameter, so the env leg is testable without os."""
    environ: Mapping[str, str] = {BINDING_ENV_VAR: "fake-a:./elsewhere"}
    assert resolve_binding(environ=environ) == "fake-a:./elsewhere"
