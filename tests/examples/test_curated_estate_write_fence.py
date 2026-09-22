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
