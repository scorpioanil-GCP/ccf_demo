"""Parity between the conformance param lists and the backend registry.

**The failure mode this module exists for.** The two conformance suites choose
which substrates they run against from parameter lists that are *hand-written*,
in two separate files: the ``graph_backend`` fixture in
``tests/conformance/test_graphstore.py`` and ``BACKEND_PARAMS`` in
``tests/conformance/test_substrate_differential.py``. An adapter that is
installed and registered but named by no param is therefore never run — and the
suite that was supposed to hold it to the D-IMPL-34 semantics and to fallback
byte-identity passes anyway, because it quietly tested one substrate fewer. The
only symptom is a test count that does not rise, which is precisely the symptom
nobody is watching. A proof that passes by not running is worth less than no
proof at all, because it is mistaken for one (15.4-RESEARCH Pitfall 7).

This is the same defect class ``D-GATE-15.3`` records three separate times: a
rule stated as a *category* ("every registered backend runs both conformance
suites"), enforced by a *hand-written enumeration* that is born incomplete and
drifts further with every arrival. The repair is never a longer enumeration; it
is an assertion that the enumeration and the category agree, which is what this
module is.

**Both directions are asserted, and both matter for different reasons.**

* Registry ⊆ params — an installed adapter no param names is the silent-pass
  case above.
* Params ⊆ registry — a param naming an adapter that is not installed is the
  loud case: it fails at boot with a resolution error rather than a parity
  error, which reports the symptom instead of the cause. Asserting this
  direction here is what turns "``demo`` errored in nine unrelated tests" into
  "the ``demo`` param names an adapter that is not installed; run
  ``make install``". It is also the assertion that makes plan 15.4-10's
  always-on install posture *load-bearing* rather than a convenience: under an
  opt-in install this direction goes red for any developer who ran
  ``make install`` and then ``make ci-core``, which is exactly why that plan
  ruled the fixture adapter always-on.

**The lists are read, never re-typed.** Both param lists are extracted from the
objects the suites actually parametrize on. Re-typing them here would create a
*third* enumeration of the same category, free to drift from the other two, and
this module would then assert that two hand-written lists agree with a third
hand-written list while the registry went unconsulted — a parity test with the
defect it exists to catch built into it.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from ccf.graph.registry import declared_names

from tests.conformance.test_graphstore import graph_backend
from tests.conformance.test_substrate_differential import BACKEND_PARAMS

pytestmark = pytest.mark.conformance


def _names_of(parameter_sets: Any, source: str) -> frozenset[str]:
    """The backend names carried by a sequence of ``pytest.param`` values.

    Fails loudly on any shape it does not understand. A helper that returned an
    empty set when it could not read the params would make every assertion in
    this module vacuously true — the failure mode one layer up, reproduced
    inside the thing built to catch it.
    """
    try:
        sets: Iterator[Any] = iter(parameter_sets)
    except TypeError as exc:  # pragma: no cover - defensive
        raise AssertionError(
            f"{source}: expected an iterable of pytest.param values, "
            f"got {type(parameter_sets).__name__}"
        ) from exc

    names: set[str] = set()
    for entry in sets:
        values = getattr(entry, "values", None)
        if values is None or len(values) != 1:  # pragma: no cover - defensive
            raise AssertionError(
                f"{source}: expected each param to carry exactly one value "
                f"(the backend name), got {entry!r}"
            )
        name = values[0]
        if not isinstance(name, str):  # pragma: no cover - defensive
            raise AssertionError(
                f"{source}: expected the param value to be a backend name, got {name!r}"
            )
        names.add(name)

    assert names, f"{source}: read no params at all"
    return frozenset(names)


def _graphstore_param_names() -> frozenset[str]:
    """The ``graph_backend`` fixture's own params, read off the fixture object.

    ``pytest.fixture(params=...)`` stores the params on a marker attached to the
    fixture function; the attribute is pytest-internal, so this reads it
    defensively and raises rather than degrading to an empty set if a pytest
    upgrade moves it. An unreadable list must fail this suite, not silence it.
    """
    marker = getattr(graph_backend, "_fixture_function_marker", None)
    if marker is None:  # pragma: no cover - defensive
        marker = getattr(graph_backend, "_pytestfixturefunction", None)
    assert marker is not None, (
        "could not read the params off the `graph_backend` fixture: neither "
        "`_fixture_function_marker` nor `_pytestfixturefunction` is present. "
        "pytest has moved the attribute; update this helper rather than "
        "re-typing the param list here."
    )
    params = getattr(marker, "params", None)
    assert params is not None, (
        "the `graph_backend` fixture marker carries no `params`; update this "
        "helper rather than re-typing the param list here."
    )
    return _names_of(params, "tests/conformance/test_graphstore.py::graph_backend")


def _differential_param_names() -> frozenset[str]:
    return _names_of(
        BACKEND_PARAMS,
        "tests/conformance/test_substrate_differential.py::BACKEND_PARAMS",
    )


def test_every_registered_adapter_is_named_by_the_graphstore_params() -> None:
    """An installed adapter no param names is a suite that passes by not running."""
    registered = frozenset(declared_names())
    assert registered, "the registry declared no adapters at all"

    missing = registered - _graphstore_param_names()
    assert not missing, (
        f"registered adapters with no param in the GraphStore conformance suite: "
        f"{sorted(missing)}. The suite passes without ever running them, and the "
        f"only symptom is a test count that does not rise. Add "
        f"`pytest.param(<name>)` to the `graph_backend` fixture — and, if the "
        f"substrate needs no container, no mark."
    )


def test_every_registered_adapter_is_named_by_the_differential_params() -> None:
    """The same hole, in the suite that pins byte-identity with the fallback."""
    registered = frozenset(declared_names())
    assert registered, "the registry declared no adapters at all"

    missing = registered - _differential_param_names()
    assert not missing, (
        f"registered adapters with no param in the substrate differential suite: "
        f"{sorted(missing)}. Byte-identity with the fallback is unasserted for "
        f"them. Add `pytest.param(<name>)` to `BACKEND_PARAMS`."
    )


def test_every_graphstore_param_names_a_registered_adapter() -> None:
    """A param naming nothing installed fails at boot, reporting the symptom."""
    registered = frozenset(declared_names())
    unknown = _graphstore_param_names() - registered

    assert not unknown, (
        f"GraphStore conformance params naming adapters that are not "
        f"registered: {sorted(unknown)}. Without this assertion the symptom is "
        f"a boot-time resolution error in every parametrized test instead of "
        f"one message naming the cause. If this is the out-of-tree fixture "
        f"adapter, run `make install` (plan 15.4-10 made that install always-on "
        f"precisely so this direction stays green)."
    )


def test_every_differential_param_names_a_registered_adapter() -> None:
    """The same direction, for the differential suite's list."""
    registered = frozenset(declared_names())
    unknown = _differential_param_names() - registered

    assert not unknown, (
        f"substrate differential params naming adapters that are not "
        f"registered: {sorted(unknown)}. Run `make install` if this is the "
        f"out-of-tree fixture adapter."
    )


def test_the_two_param_lists_agree_with_each_other() -> None:
    """Two hand-written lists of one category drift; this is where that shows.

    Both are already pinned to the registry above, so this cannot fail on its
    own — which is the point of stating it: it names the invariant the two
    assertions above jointly imply, so a future change that relaxes one of them
    does not quietly relax this too.
    """
    graphstore = _graphstore_param_names()
    differential = _differential_param_names()

    assert graphstore == differential, (
        f"the two conformance param lists disagree. Only in GraphStore: "
        f"{sorted(graphstore - differential)}; only in differential: "
        f"{sorted(differential - graphstore)}."
    )


def test_the_out_of_tree_adapter_is_among_the_registered_names() -> None:
    """The non-vacuity check for this whole module (D-11, V8).

    Every assertion above compares the params to whatever the registry happens
    to declare. If the registry declared only the six built-in adapters, all of
    them would pass while the phase's central claim — that a genuinely
    out-of-tree adapter runs the same conformance suites — went untested. This
    states the precondition as itself, and it fails rather than skips: a missing
    install is a broken proof, not an absent one.
    """
    registered = frozenset(declared_names())
    assert "demo" in registered, (
        "the out-of-tree fixture adapter `demo` is not registered, so the "
        "conformance suites are running against built-in adapters only and the "
        "D-11 zero-cost claim is unproven. Install it with `make install`, or "
        "`pip install -e ./tests/fixtures/ccf-demo-adapter`."
    )
