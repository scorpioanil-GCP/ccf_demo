"""The curated estate is READ-ONLY, and the fence that makes it so runs once.

**CLAUDE.md §9 and `D-IMPL-318` state the rule absolutely** — examples and
their tests READ the curated `.76` estate; anything that must WRITE writes to a
local, disposable store named by ``CCF_TEST_FLUREE_URL`` /
``CCF_TEST_POSTGRES_DSN``. *"Nothing seeds `.76`, ever."*

**It was stated, and partly enforced.**
``tests/examples/estate_guard.py::refuse_to_write_the_curated_estate`` refuses
a seed whose target names a curated host — but only for the modules that
import it, and measured 2026-09-22 **two of the nine** modules naming
``CCF_TEST_*`` did.

**And the nine were never the whole exposure.** A test can reach the
disposable store through its example's own ``artifacts/backends.yaml`` without
naming the variable anywhere — which is exactly how
``test_s1_01_governed_resolver_adoption.py`` appended **134 transactions to
the curated `ccf:main` ledger** (``t`` 1474 → 1608) during the
release-hardening sweep, from an environment script that had mapped
``CCF_TEST_FLUREE_URL`` onto ``.76`` by pattern. Fluree is append-only, so
those transactions are permanent. No per-module call site could have caught
it: the module never mentions the variable.

So the fence moved to ``tests/conftest.py`` as a session-scoped autouse
fixture. It runs **once, before any test can write**, and refuses the run
rather than a call. This module proves it — in subprocesses, because by the
time a test in this session executes, the fence has already passed for this
session.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: A node that neither reads nor writes an estate, so the ONLY thing that can
#: stop the session is the fence itself.
INERT_NODE = (
    "tests/examples/test_product_tree_import_isolation.py"
    "::test_every_shipped_binder_owns_its_process_or_proves_what_it_loaded"
)

CURATED = "192.168.4.76"


def _run(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", INERT_NODE, "-q", "-p", "no:randomly"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=300,
        env={**os.environ, **env},
    )


def test_a_disposable_fluree_on_a_curated_host_refuses_the_whole_session() -> None:
    """The exact misconfiguration that wrote to `ccf:main`, now refused.

    The fence names the variable, the host, and why it matters — that a seeded
    Fluree ledger is PERMANENT — so the operator who misconfigured a run is
    told what to change rather than left to infer it.
    """
    completed = _run({"CCF_TEST_FLUREE_URL": f"http://{CURATED}:8090"})
    assert completed.returncode != 0, (
        "a disposable-store variable pointed at the curated estate did not"
        " stop the session"
    )
    output = completed.stdout + completed.stderr
    assert "refusing to SEED a curated store" in output, output[-1500:]
    assert CURATED in output


def test_a_disposable_postgres_on_a_curated_host_refuses_too() -> None:
    """Both legs, independently — whatever the operator exported.

    `D-IMPL-318`'s wording is *"on either leg independently"*, and a fence
    that only watched Fluree would leave the schema leg open.
    """
    completed = _run(
        {"CCF_TEST_POSTGRES_DSN": f"host={CURATED} port=5432 dbname=parkavedb"}
    )
    assert completed.returncode != 0, "the Postgres leg was not fenced"
    assert "refusing to SEED a curated store" in completed.stdout + completed.stderr


def test_the_refusal_does_not_publish_the_credential() -> None:
    """A DSN carries a password, and this fence is designed to be LOUD.

    It raises, pytest prints it once per erroring test, and CI keeps the
    output — so an unredacted DSN here would publish the estate's credential
    every time somebody misconfigured a run.
    """
    secret = "hunter2-not-a-real-password"
    completed = _run(
        {"CCF_TEST_POSTGRES_DSN": f"postgresql://parkave:{secret}@{CURATED}:5432/parkavedb"}
    )
    output = completed.stdout + completed.stderr
    assert "refusing to SEED a curated store" in output
    assert secret not in output, "the fence printed the credential it was handed"
    assert ":***@" in output, "the fence did not redact; it merely omitted"


def test_a_local_disposable_store_is_not_refused() -> None:
    """THE POSITIVE CONTROL, and without it this module proves nothing.

    A fence that refused every configuration would pass all three tests above
    and be useless. ``localhost`` is the documented default and must run
    through — whether the container behind it is up is a different question,
    and this inert node does not ask it.
    """
    completed = _run({"CCF_TEST_FLUREE_URL": "http://localhost:8090"})
    output = completed.stdout + completed.stderr
    assert "refusing to SEED a curated store" not in output, output[-1000:]
    assert completed.returncode == 0, output[-1500:]


def test_the_curated_host_list_is_configuration_not_a_constant() -> None:
    """A second estate is a configuration change, not a code change.

    ``CCF_CURATED_ESTATE_HOSTS`` widens the fence. Asserted by fencing a host
    that is NOT curated by default and showing the refusal follows the
    declaration rather than a literal.
    """
    other = "10.99.99.99"
    permissive = _run({"CCF_TEST_FLUREE_URL": f"http://{other}:8090"})
    assert permissive.returncode == 0, (
        "an uncurated host was refused; the fence is matching something other"
        " than its declaration"
    )
    declared = _run(
        {
            "CCF_TEST_FLUREE_URL": f"http://{other}:8090",
            "CCF_CURATED_ESTATE_HOSTS": other,
        }
    )
    assert declared.returncode != 0, "declaring a curated host did not fence it"
    assert "refusing to SEED a curated store" in declared.stdout + declared.stderr


def test_every_module_naming_the_disposable_store_is_now_covered() -> None:
    """The measurement that motivated moving the fence, kept executable.

    Two of nine modules called the guard. The fence is session-scoped now, so
    coverage is no longer a function of how many call sites remembered — and
    this test states the count so the claim is checkable rather than asserted.
    """
    naming = sorted(
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "tests").rglob("*.py")
        if "__pycache__" not in path.parts
        and any(
            name in path.read_text(encoding="utf-8")
            for name in ("CCF_TEST_FLUREE_URL", "CCF_TEST_POSTGRES_DSN")
        )
    )
    assert len(naming) >= 9, naming
    conftest = (REPO_ROOT / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert "refuse_to_write_the_curated_estate" in conftest, (
        "the session fence is gone from tests/conftest.py; coverage would fall"
        " back to whichever modules happen to import the guard"
    )
    assert 'scope="session", autouse=True' in conftest, (
        "the fence is no longer session-scoped and autouse, so a module that"
        " does not request it writes unfenced"
    )
    assert json.dumps(naming)  # the roster is enumerated, never counted alone


# --------------------------------------------------------------------------
# D-IMPL-358 ruling 12 — the fence compares HOSTS, not substrings, and covers
# every disposable-store variable.
# --------------------------------------------------------------------------


def test_the_fence_covers_every_disposable_store_variable_including_mongo() -> None:
    """`CCF_TEST_MONGO_URI` was defined and NOT fenced (`D-IMPL-358` ruling 12).

    Eight estate-gated trees read curated Mongo `fibo_v2`, so the one store the
    session fence did not cover was a store the suite actually reaches. Asserted
    as a ROSTER rather than a count, because a right count with a wrong member
    audits clean forever.
    """
    from tests.conftest import DISPOSABLE_STORE_ENV, MONGO_URI_ENV

    assert set(DISPOSABLE_STORE_ENV) == {
        "CCF_TEST_FLUREE_URL",
        "CCF_TEST_POSTGRES_DSN",
        MONGO_URI_ENV,
    }


@pytest.mark.parametrize(
    "target",
    [
        "http://192.168.4.76:8090",
        "http://192.168.4.76:8091",
        "postgresql://u:pw@192.168.4.76:5432/ccf_v2",
        "host=192.168.4.76 port=5432 dbname=ccf_v2 user=u password=pw",
        "hostaddr=192.168.4.76 port=5432 dbname=ccf_v2",
        "host=h1,192.168.4.76 port=5432,5433 dbname=ccf_v2",
        "postgresql://u:pw@h1:5432,192.168.4.76:5433/db",
        "mongodb://192.168.4.76:27017",
        "mongodb://a:27017,192.168.4.76:27017/db",
        "192.168.4.76:8090",
    ],
    ids=[
        "fluree",
        "fluree-peer",
        "dsn-uri",
        "dsn-libpq",
        "dsn-hostaddr",
        "dsn-multihost-keyword",
        "dsn-multihost-uri",
        "mongo",
        "mongo-multihost",
        "bare",
    ],
)
def test_a_curated_target_is_refused_in_every_serialization(target: str) -> None:
    """Both PostgreSQL serializations, because knowing one proves nothing about
    the other.

    Wave 1 paid for this directly: a credential sweep that knew only the URI form
    reported "no DSN points at the estate" while a **libpq keyword-form** DSN was
    sitting in a census log. A fence that parses one form and not the other has a
    hole exactly the shape of the form it does not parse.
    """
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    with pytest.raises(RuntimeError, match="refusing to SEED a curated store"):
        refuse_to_write_the_curated_estate(target)


def test_a_curated_host_inside_a_PASSWORD_is_not_a_curated_TARGET() -> None:
    """The substring test's false positive, pinned (`D-IMPL-358` ruling 12).

    `any(host in target for host in curated)` answered True for this DSN because
    the curated address appears in the password. The host is `localhost`; the
    write goes to a throwaway container; refusing it would stop a legitimate run
    and teach the operator that the fence is noise.
    """
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    refuse_to_write_the_curated_estate(
        "postgresql://u:192.168.4.76@localhost:5432/test"
    )


def test_curated_protection_is_HOST_LEVEL_and_no_port_rule_exists() -> None:
    """The estate rule is *"the curated host is read-only"*, not *"on certain
    ports"* (`D-IMPL-358` ruling 12 as corrected).

    An earlier draft of this fence treated a curated declaration carrying a port
    as fencing **only** that port. That invented a port policy nobody ruled and
    narrowed a host-level protection into a port list — a weakening dressed as
    precision. This control pins the opposite: a declaration that happens to
    carry a port still fences **every** port on that host, and a declaration
    without one behaves identically.
    """
    from tests.examples.estate_guard import (
        CURATED_HOSTS_ENV,
        refuse_to_write_the_curated_estate,
    )

    previous = os.environ.get(CURATED_HOSTS_ENV)
    os.environ[CURATED_HOSTS_ENV] = "192.168.4.76:8091"
    try:
        for port in (8090, 8091, 5432, 27017):
            with pytest.raises(RuntimeError, match="refusing to SEED a curated store"):
                refuse_to_write_the_curated_estate(f"http://192.168.4.76:{port}")
    finally:
        if previous is None:
            del os.environ[CURATED_HOSTS_ENV]
        else:
            os.environ[CURATED_HOSTS_ENV] = previous


def test_an_UNPARSEABLE_target_fails_CLOSED() -> None:
    """*Don't know* must never collapse into *pass*.

    A target whose destination cannot be established is a target nobody has
    checked, so the fence refuses it rather than admitting it.

    The carrier is a target that yields NO destination at all. A malformed port
    is deliberately NOT the carrier any more: the authority is now split
    structurally rather than through `urlsplit(...).port`, so
    `http://192.168.4.76:not-a-port` is correctly classified as the curated host
    and refused for the right reason — which is a better outcome than being
    refused for being unreadable.
    """
    from tests.examples.estate_guard import refuse_to_write_the_curated_estate

    with pytest.raises(RuntimeError, match="refusing to SEED a curated store"):
        refuse_to_write_the_curated_estate("   ")
