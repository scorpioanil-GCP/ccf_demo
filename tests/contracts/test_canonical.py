"""Canonical-serializer tests (04-RESEARCH.md Pattern 3 bit-for-bit prerequisite).

`ccf.contracts.canonical` is the ONE canonical form in the SDK: composition
preservation (FABR-02), D-IMPL-26 content addressing, and replay hashes all
compare against it, so order-independence and cross-process stability are
invariants, not conveniences.

The cross-process test spawns a child, and a child's environment is a fact
------------------------------------------------------------------------------
:func:`test_hash_is_stable_across_processes` is the only test here that leaves
this interpreter, and until ``D-IMPL-150`` (Dave, 2026-08-17) it spawned with
``env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"}`` — **no**
``PYTHONPATH``. That is the identical blind spot plan ``17-10`` measured and
fixed one layer over, in :meth:`~ccf.client.adapters.mcp_stdio.McpStdioAdapter._call`:
``mcp.client.stdio`` hands a child six variables, ``PYTHONPATH`` is not among
them, and a smoke run reported byte-identical content addresses **while the
child was executing a different checkout's** ``ccf`` through the environment's
editable install.

Under worktree execution — how every executor in this project runs — that made
this test a statement about code its executor had not written, reported green.
So :func:`child_environment` is now the one place a child's environment is
decided, and :func:`test_the_child_resolves_the_same_ccf_this_test_is_running`
is where that is watched.

**The minimality is preserved, not traded away.** The environment is deliberately
small because the test pins ``PYTHONHASHSEED`` to prove hash-order independence,
and a child inheriting the parent's whole environment would inherit a
``PYTHONHASHSEED`` the parent happened to carry. Exactly one variable was added,
it is propagated only when the parent has one, and
:func:`test_the_child_environment_states_only_what_it_needs` holds the set closed.
"""

from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

import ccf
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import (
    CanonicalizationError,
    canonical_bytes,
    content_hash,
)

#: Everything a child spawned from this module may be told. Closed, and asserted
#: closed: a variable added here is a decision somebody makes on purpose.
PERMITTED_CHILD_VARIABLES = frozenset({"PYTHONHASHSEED", "PATH", "PYTHONPATH"})

#: What the set is when the parent carries no ``PYTHONPATH`` to propagate. Named
#: rather than spelled inline so the two halves of
#: :func:`test_the_child_environment_states_only_what_it_needs` are two
#: *expectations* rather than one expectation and one subtraction.
PERMITTED_WITHOUT_PYTHONPATH = PERMITTED_CHILD_VARIABLES - {"PYTHONPATH"}


def assert_child_environment_is_exactly(
    carried: Mapping[str, str], expected: frozenset[str], *, when: str
) -> None:
    """The child was told exactly ``expected`` — no more, and **no fewer**.

    ``D-IMPL-151`` finding ``B3``. This read ``set(carried) <= expected``, which
    is one-sided: it fires on a variable that was added and cannot fire on one
    that went missing. The claim the module docstring makes is *"holds the set
    closed"*, and a subset test holds only half of it — a
    :func:`child_environment` that stopped propagating ``PYTHONPATH`` would
    reintroduce the ``D-IMPL-150`` defect this very module exists to have fixed,
    and the assertion watching for it would have stayed green. That is this
    repository's recurring defect class — a check that stops checking without
    going red — so the comparison is now equality in both directions.

    Written as a function taking its subject as a parameter (``D-22``) so the
    control below can hand it a divergent environment and watch **this** code
    fail, rather than a copy of it.

    Args:
        carried: The environment a child would be launched with.
        expected: Exactly the variable names that environment must carry.
        when: The condition this expectation holds under, for the message.

    Raises:
        AssertionError: the environment carries a variable that is not expected,
            or is missing one that is.
    """
    names = set(carried)
    if names == set(expected):
        return
    extra = sorted(names - set(expected))
    missing = sorted(set(expected) - names)
    raise AssertionError(
        f"the child environment {when} is not the closed set it claims to be —"
        f" unexpected {extra}, missing {missing}. An unexpected variable lets a"
        " child inherit a decision the parent happened to carry; a missing one"
        " is `D-IMPL-150` reintroduced, where a child resolves `ccf` through"
        " whatever editable install its interpreter finds and answers"
        " correctly from code nobody is testing"
    )


def child_environment(seed: str) -> dict[str, str]:
    """The environment a child of this module runs under.

    Three variables at most, and each is here for a stated reason:

    * ``PYTHONHASHSEED`` — **pinned to** ``seed``, which is the whole subject of
      :func:`test_hash_is_stable_across_processes`. Never inherited: a parent
      carrying its own seed would decide the value the test is varying.
    * ``PATH`` — a minimal one, because the child runs an interpreter given by
      absolute path and needs nothing else found for it.
    * ``PYTHONPATH`` — **propagated when the parent has one, absent when it does
      not.** This is the ``D-IMPL-150`` repair. Without it a child resolves
      ``ccf`` through whatever editable install the interpreter carries, which
      in a worktree is another checkout entirely — and it answers correctly from
      code nobody is testing.

    Args:
        seed: The ``PYTHONHASHSEED`` this child must run under, as text.

    Returns:
        A fresh mapping. Never the parent's, and never shared between calls.
    """
    environment = {"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"}
    inherited = os.environ.get("PYTHONPATH")
    if inherited is not None:
        environment["PYTHONPATH"] = inherited
    return environment


class _Doc(CCFContract):
    b: str
    a: str
    tags: frozenset[str]


def test_mapping_key_order_does_not_affect_bytes() -> None:
    left = canonical_bytes({"a": 1, "b": 2, "c": {"y": 1, "x": 2}})
    right = canonical_bytes({"c": {"x": 2, "y": 1}, "b": 2, "a": 1})
    assert left == right


def test_set_element_order_does_not_affect_bytes() -> None:
    left = canonical_bytes({"tags": {"z", "a", "m"}})
    right = canonical_bytes({"tags": {"m", "z", "a"}})
    assert left == right


def test_sequence_order_is_significant() -> None:
    assert canonical_bytes([1, 2]) != canonical_bytes([2, 1])


def test_model_and_equivalent_mapping_agree() -> None:
    doc = _Doc(a="1", b="2", tags=frozenset({"x", "y"}))
    assert canonical_bytes(doc) == canonical_bytes(
        {"a": "1", "b": "2", "tags": {"y", "x"}}
    )


def test_timestamps_serialize_as_fixed_precision_rfc3339_utc() -> None:
    aware_utc = datetime(2026, 7, 25, 12, 0, 0, tzinfo=UTC)
    offset = aware_utc.astimezone(timezone(timedelta(hours=-5)))
    assert canonical_bytes({"t": aware_utc}) == canonical_bytes({"t": offset})
    assert b'"2026-07-25T12:00:00.000000Z"' in canonical_bytes({"t": aware_utc})


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_bytes({"t": datetime(2026, 7, 25, 12, 0, 0)})


def test_floats_are_rejected() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_bytes({"amount": 1.5})


def test_decimal_is_accepted_and_order_stable() -> None:
    assert canonical_bytes({"amount": Decimal("1.50")}) == b'{"amount":"1.50"}'


def test_unsupported_type_is_rejected() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_bytes({"x": object()})


def test_content_hash_matches_sha256_of_canonical_bytes() -> None:
    payload = {"a": 1, "b": ["x", "y"]}
    assert (
        content_hash(payload)
        == hashlib.sha256(canonical_bytes(payload)).hexdigest()
    )


def test_content_hash_is_64_char_lowercase_hex() -> None:
    digest = content_hash({"a": 1})
    assert len(digest) == 64
    assert digest == digest.lower()
    assert all(c in "0123456789abcdef" for c in digest)


def test_known_input_digest_is_pinned() -> None:
    # Pins the canonical form itself: {"a":1} with compact separators.
    assert canonical_bytes({"a": 1}) == b'{"a":1}'
    assert (
        content_hash({"a": 1})
        == hashlib.sha256(b'{"a":1}').hexdigest()
    )


def test_hash_is_stable_across_processes() -> None:
    program = (
        "from ccf.contracts.canonical import content_hash;"
        "print(content_hash({'b': {'z', 'a'}, 'a': 1}))"
    )
    runs = {
        subprocess.run(
            [sys.executable, "-c", program],
            capture_output=True,
            text=True,
            check=True,
            env=child_environment(seed),
        ).stdout.strip()
        for seed in ("0", "1", "12345")
    }
    assert len(runs) == 1
    assert runs.pop() == content_hash({"b": {"z", "a"}, "a": 1})


# ---------------------------------------------------------------------------
# `D-IMPL-150` — what the child above is actually running.
#
# A cross-process stability claim is a claim about two runs of THE SAME code.
# The three tests below are what makes that the case rather than the hope.
# ---------------------------------------------------------------------------


def test_the_child_resolves_the_same_ccf_this_test_is_running() -> None:
    """The defect, stated as a property: same interpreter, same ``ccf``.

    ``17-10`` measured this exact failure one layer over — a child stripped of
    ``PYTHONPATH`` imported a different checkout's ``ccf`` through the
    environment's editable install and answered every question perfectly, from
    code the test was not exercising. Under worktree execution this test's own
    child did the same, and reported green while doing it.
    """
    completed = subprocess.run(
        [sys.executable, "-c", "import ccf; print(ccf.__file__)"],
        capture_output=True,
        text=True,
        check=True,
        env=child_environment("0"),
    )
    assert (
        pathlib.Path(completed.stdout.strip()).resolve()
        == pathlib.Path(ccf.__file__).resolve()
    )


def test_a_child_without_pythonpath_cannot_see_what_the_parents_names(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """**The control.** The fix is watched working against the bug it repairs.

    A sentinel module reachable only through the parent's ``PYTHONPATH``, and
    two children: one launched from :func:`child_environment` and one from the
    environment this module used to build. The first imports it; the second
    cannot. Deterministic in any checkout, because the sentinel is created here
    rather than depended upon — asserting on ``ccf``'s own location would prove
    nothing in a tree where both resolutions land on the same file.
    """
    (tmp_path / "ccf_canonical_sentinel.py").write_text(
        "MARKER = 'reached'\n", encoding="utf-8"
    )
    monkeypatch.setenv(
        "PYTHONPATH",
        os.pathsep.join(
            [str(tmp_path), *filter(None, [os.environ.get("PYTHONPATH")])]
        ),
    )
    program = "import ccf_canonical_sentinel as s; print(s.MARKER)"

    carried = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        env=child_environment("0"),
    )
    assert carried.returncode == 0, carried.stderr
    assert carried.stdout.strip() == "reached"

    stripped = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        env={"PYTHONHASHSEED": "0", "PATH": "/usr/bin:/bin"},
    )
    assert stripped.returncode != 0, (
        "a child with no `PYTHONPATH` imported a module only the parent's"
        " `PYTHONPATH` names — the control cannot fail, so it proves nothing"
    )
    assert "ModuleNotFoundError" in stripped.stderr


def test_the_child_environment_states_only_what_it_needs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The seed stays pinned and the set stays closed.

    The environment is minimal on purpose — a child inheriting the parent's
    whole environment would inherit a ``PYTHONHASHSEED`` the parent happened to
    carry, and the seed is the variable
    :func:`test_hash_is_stable_across_processes` is varying. So the repair adds
    one variable, propagates it only when there is one to propagate, and this
    holds both halves.

    **Both halves compare the set exactly** (``D-IMPL-151`` finding ``B3``).
    They read ``set(...) <= PERMITTED_CHILD_VARIABLES``, which could fail only
    on an *added* variable — so the half of the claim that matters most, that
    ``PYTHONPATH`` is still being propagated, was carried by the one-line
    membership check beside it and by nothing else in the absent case.
    """
    monkeypatch.setenv("PYTHONPATH", "/somewhere")
    carried = child_environment("12345")
    assert carried["PYTHONHASHSEED"] == "12345"
    assert carried["PYTHONPATH"] == "/somewhere"
    assert_child_environment_is_exactly(
        carried, PERMITTED_CHILD_VARIABLES, when="with a `PYTHONPATH` to carry"
    )

    monkeypatch.delenv("PYTHONPATH")
    absent = child_environment("0")
    assert "PYTHONPATH" not in absent
    assert_child_environment_is_exactly(
        absent, PERMITTED_WITHOUT_PYTHONPATH, when="with no `PYTHONPATH` to carry"
    )


def test_control_a_child_environment_missing_a_variable_is_refused() -> None:
    """**The control.** The repaired assertion fires on an *omission*.

    The divergent subject is the environment ``child_environment`` built before
    ``D-IMPL-150`` — seed and ``PATH``, no ``PYTHONPATH`` — handed to the same
    function the test above calls, under the expectation that holds when the
    parent has one to propagate. Against the one-sided ``<=`` comparison this
    case passed, which is precisely why it is the control.
    """
    regressed = {"PYTHONHASHSEED": "0", "PATH": "/usr/bin:/bin"}

    assert set(regressed) <= PERMITTED_CHILD_VARIABLES, (
        "the pre-`D-IMPL-150` environment satisfies the subset comparison this"
        " control exists to show is insufficient — if it did not, the control"
        " would be proving something else"
    )
    with pytest.raises(AssertionError, match="missing"):
        assert_child_environment_is_exactly(
            regressed, PERMITTED_CHILD_VARIABLES, when="under the control"
        )


def test_control_a_child_environment_carrying_an_extra_variable_is_refused() -> None:
    """The other side of the same comparison, kept explicitly.

    Equality replaced a subset test, so the case the subset test *could*
    already catch is asserted here rather than assumed to have survived the
    change.
    """
    leaked = {
        "PYTHONHASHSEED": "0",
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": "/somewhere",
        "AWS_SECRET_ACCESS_KEY": "inherited-from-the-parent",
    }

    with pytest.raises(AssertionError, match="unexpected"):
        assert_child_environment_is_exactly(
            leaked, PERMITTED_CHILD_VARIABLES, when="under the control"
        )


def test_modules_are_tagged_algorithmic() -> None:
    import ccf.contracts.base as base_mod
    import ccf.contracts.canonical as canonical_mod

    assert base_mod.__ccf_mode__ == "algorithmic"
    assert canonical_mod.__ccf_mode__ == "algorithmic"
