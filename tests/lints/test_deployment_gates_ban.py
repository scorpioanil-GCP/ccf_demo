"""``cinv02-deployment-gates`` — ccf.deployment may not import ccf.products.gates.

D-15A. :func:`ccf.products.gates.run_gates` compares the product's declared
lineage — the Control Plane claim, transcribed into the Contract — against the
projection engine's resolved operator set. That comparison verifies
**assembly-path integrity** rather than independent witness: the engine builds
its invoked set and its steps in one loop over the same operator plan, so it is
a faithful transcriber of the plan (``D-IMPL-86``; the ``D-IMPL-57`` correction
of 2026-08-05). It is a check only while the two arguments are separately
assembled by the deployment. A wiring helper that ran the gate is one step from
deriving both from one input, at which point there is nothing left to compare —
not even a transcription — and the gate compares a value against itself: green,
tautological, and a whitepaper invariant (§7.6, INV-CH7-47) gone with nothing
failing to say so. Gate execution stays in adopter code. **Authorable** drift is
refused upstream, at
:func:`ccf.deployment.binder.refuse_operator_set_divergence`.

All three tests drive the same ``tools.lints.__main__.run`` entrypoint CI uses,
against synthetic tmp trees, so they prove the rule as executed rather than as
configured. The third is the opposite-direction regression guard: the ban is on
one importer, and a rule that had quietly widened into a general ban on naming
the gate module would pass the first two tests and fail this one.
"""

from __future__ import annotations

import pathlib

from tools.lints.harness_imports import (
    GATES_DENIED_IMPORTER,
    GATES_MODULE,
    RULE_DEPLOYMENT_GATES,
)
from tools.lints.__main__ import RULE_TREE_SCOPE, run


def _write(base: pathlib.Path, rel: str, source: str) -> None:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


# --- Test 1: the ban fires inside ccf.deployment ------------------------------


def test_a_deployment_module_importing_the_gates_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    assert "src" in RULE_TREE_SCOPE["harness-imports"]

    _write(
        tmp_path,
        "src/ccf/deployment/x.py",
        "import ccf.products.gates\n",
    )
    findings = run(tmp_path, ["harness-imports"])
    assert findings, f"{GATES_DENIED_IMPORTER} may not import {GATES_MODULE}"
    assert any(RULE_DEPLOYMENT_GATES in f for f in findings)


# --- Test 2: `from X import <submodule>` is caught too ------------------------


def test_the_from_import_form_is_caught_as_well(tmp_path: pathlib.Path) -> None:
    """``from ccf.products import gates`` binds the same module.

    The shared ``imported_module_names`` helper reports only ``ccf.products``
    for this form — correctly, since it cannot tell a submodule from an
    attribute — so the rule supplements it. Without this test the ban would be
    a one-spelling ban, which is not a ban.
    """
    _write(
        tmp_path,
        "src/ccf/deployment/manifest.py",
        "from ccf.products import gates\n",
    )
    findings = run(tmp_path, ["harness-imports"])
    assert any(RULE_DEPLOYMENT_GATES in f for f in findings)

    _write(
        tmp_path,
        "src/ccf/deployment/other.py",
        "from ccf.products.gates import run_gates\n",
    )
    findings = run(tmp_path, ["harness-imports"])
    assert (
        len([f for f in findings if RULE_DEPLOYMENT_GATES in f]) == 2
    ), "both the submodule form and the from-module form must be caught"


# --- Test 3: the opposite-direction regression guard --------------------------


def test_the_ban_did_not_widen_beyond_ccf_deployment(
    tmp_path: pathlib.Path,
) -> None:
    """Everything except ``ccf.deployment`` may still name the gate module.

    ``ccf.products.serve`` is the worked case: the delivery path's whole job is
    to hand a ``ServableProduct`` onward, so it necessarily names the gates. A
    rule that fired here would have inverted from a targeted denial into a
    general prohibition on the SDK's own gate module.
    """
    _write(
        tmp_path,
        "src/ccf/products/serve.py",
        "from ccf.products.gates import run_gates\nimport ccf.products.gates\n",
    )
    _write(
        tmp_path,
        "src/ccf/deployment_evil/x.py",
        "import ccf.products.gates\n",
    )
    findings = run(tmp_path, ["harness-imports"])
    assert [f for f in findings if RULE_DEPLOYMENT_GATES in f] == [], (
        "the ban names one importer; matching is dot-bounded, so neither"
        " ccf.products.serve nor the sibling ccf.deployment_evil is caught"
    )
