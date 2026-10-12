# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""cp-00 … cp-04 — the operator-set check they no longer write is performed by the SDK, per example.

Dave, 2026-10-11 20:19 MST, ruling 4, verbatim: *"Approve cp-00 through cp-04's
code-shape exemptions where the SDK now performs the delegated step. Name that step
and its replacement behavioral coverage. Exemption from an obsolete source-layout
requirement is permitted; exemption from the actual security or business requirement
is not."*

The obsolete source-layout requirement: `tests/products/test_gate_two_call_shape.py`'s
tripwire (2) demands that a body building a projection plan NAME
:func:`ccf.deployment.refuse_operator_set_divergence` before it executes the plan
(`D-IMPL-86`). Since their 2026-10-11 compatibility repairs the five frozen specimens
build no plan they execute: each hands a named ``plan_factory`` to
:func:`ccf.products.resolver.build_governed_resolver`, whose resolver calls the binder
between ``plan_factory(required=…)`` and ``ProjectionEngine.execute`` (`D-IMPL-300`),
then runs Gate 2 in :func:`ccf.products.gates.run_gates` against the engine's own
resolution. That is the DELEGATED STEP.

The business requirement it protects: **a product is never assembled from an
operator set its own product class does not claim.** This module proves the SDK
still enforces it FOR EACH SPECIMEN, behaviorally, on the live estate, by running
the specimen's own documented ``run.py`` twice through one driver:

* **control** — unchanged: the default question SERVES and prints its address;
* **contradiction** — ``build_governed_resolver`` is wrapped so the specimen's own
  ``plan_factory`` receives ``required`` plus one operator the class does not
  claim: the SDK's binder refuses with ``operator set divergence``, raised from
  the resolver, and nothing is served.

The SDK-level coverage of the same step (fixture scale) is
``tests/products/test_resolver_seam.py::test_a_plan_contradicting_the_class_is_refused_before_it_is_executed``
(the binder refuses BEFORE the plan is invoked) and
``tests/products/test_gate_independence.py::test_perturbing_engine_resolved_is_refused_and_the_declared_set_is_not``
(Gate 2). ``test_gate_two_call_shape.py::DELEGATED_STEP_COVERAGE`` names all of them
per specimen and asserts they exist.

**Reads the estate, seeds nothing.**
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLES = REPO_ROOT / "examples"

#: Specimen → the estate variables its documented command reads.
SPECIMENS = {
    "cp-00-institutional-holders": ("CCF_CP_00_POSTGRES_DSN",),
    "cp-01-counterparty-reference-snapshot": ("CCF_CP_01_POSTGRES_DSN",),
    "cp-02-facility-terms-snapshot": ("CCF_CP_02_POSTGRES_DSN",),
    "cp-03-obligor-financial-spread": ("CCF_CP_03_POSTGRES_DSN",),
    "cp-04-corporate-family-tree": (
        "CCF_CP_04_FLUREE_URL", "CCF_CP_04_FLUREE_LEDGER", "CCF_CP_04_POSTGRES_DSN", "CCF_CP_04_POSTGRES_SCHEMA",
    ),
}

#: Test vocabulary: an operator key no product class in the suite claims.
UNCLAIMED = "traversal.r5-an-operator-the-class-does-not-claim"

_DRIVER = """
import pathlib, sys
tree, mode, unclaimed = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
sys.path.insert(0, str(tree))
import ccf.products.resolver as resolver
original = resolver.build_governed_resolver

def build_governed_resolver(*args, plan_factory, **kwargs):
    def contradicting(*, required, request):
        return plan_factory(required=tuple(required) + (unclaimed,), request=request)
    return original(*args, plan_factory=contradicting if mode == "contradict" else plan_factory, **kwargs)

resolver.build_governed_resolver = build_governed_resolver   # before the specimen imports it
sys.argv = [str(tree / "run.py")]
import run
raise SystemExit(run.main())
"""

_SERVED_ADDRESS = re.compile(r"content address\s+[0-9a-f]{64}")


def _run(tree: str, mode: str) -> subprocess.CompletedProcess[str]:
    missing = [name for name in SPECIMENS[tree] if not os.environ.get(name)]
    if missing:
        message = f"the live estate is not configured: {', '.join(missing)} unset (CLAUDE.md §9)"
        if os.environ.get("CCF_REQUIRE_ESTATE"):
            pytest.fail(message)
        pytest.skip(message)
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(str(REPO_ROOT / part) for part in ("src", "runtime"))}
    return subprocess.run(
        [sys.executable, "-B", "-c", _DRIVER, str(EXAMPLES / tree), mode, UNCLAIMED],
        capture_output=True, text=True, env=env, cwd=REPO_ROOT, timeout=600,
    )


@pytest.mark.parametrize("tree", sorted(SPECIMENS))
def test_the_sdk_refuses_a_plan_the_class_does_not_claim_for_each_frozen_specimen(tree: str) -> None:
    control = _run(tree, "control")
    assert control.returncode == 0, control.stdout[-1500:] + control.stderr[-1500:]
    assert _SERVED_ADDRESS.search(control.stdout), f"{tree}'s control did not serve:\n{control.stdout[-1500:]}"

    refused = _run(tree, "contradict")
    assert refused.returncode != 0, f"{tree} served from an operator set its class does not claim"
    assert not _SERVED_ADDRESS.search(refused.stdout), f"{tree} printed a served address under contradiction"
    # The refusal is the SDK BINDER's, raised from inside the governed resolver —
    # not a gate further on, and nothing the specimen wrote.
    assert "ValueError: operator set divergence" in refused.stderr, refused.stderr[-2000:]
    assert UNCLAIMED in refused.stderr
    trace = refused.stderr
    assert "ccf/products/resolver.py" in trace and "refuse_operator_set_divergence" in trace, trace[-2000:]
    assert f"examples/{tree}" not in trace.split("refuse_operator_set_divergence")[-1], (
        "the binder frame is not the last before the raise"
    )
