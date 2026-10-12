# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Every debt-tolerance calibration changed on 2026-10-11, shown with BOTH outcomes, on the live estate.

Dave, 2026-10-11 20:19 MST, ruling 3, verbatim: *"For each changed calibration, show
both outcomes: the labelled illustrative values and the served result; the original
stricter values—or clearly stated realistic deployment values—and the resulting
refusal. Do not describe illustrative settings as bank-approved production policy.
Change example declarations, not the SDK's enforcement."*

The calibrations (17:34 *"raise the tolerance so they serve"*; 17:51 *"approved to
move all tolerances as required to demonstrate the examples"*;
`examples/AMENDMENTS-2026-10-11.md`):

* cp-01 — the default question's `debt_tolerance` 0.25 → **0.30** (`artifacts/question.yaml`);
* cp-02 — the no-maturity facility asked at **0.65** (the question's own 0.25 unchanged);
* cp-03 — the default question's `debt_tolerance` 0.25 → **0.90** (`artifacts/question.yaml`);
* cp-03-canonical — `run.py --debt-tolerance` default **0.90** (CP-14's own 0.25 refused).

Each case runs the example's OWN documented program (`run.py`, the command the
README and the Makefile name) against `.76`, read-only, twice: at the illustrative
value it SERVES and prints its Context Debt; at the original 0.25 it is REFUSED
`tolerance-exceeded` by name with a replay reference. The assertions are
relationships, never pinned estate numbers (CLAUDE.md §9): the measured `D_c` lies
above the original value and at or below the illustrative one — which is exactly
why one serves and the other refuses.

The cp-11 window and expiry and the cp-14 demonstration time are shown both ways in
their own modules (`test_cp_11_output.py`, `test_cp_14_demonstration_clock.py`).

**Reads the estate, seeds nothing.**
"""

from __future__ import annotations

import ast
import os
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass
from decimal import Decimal

import pytest
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLES = REPO_ROOT / "examples"

#: The value every one of these questions carried before the 2026-10-11 calibration.
ORIGINAL = Decimal("0.25")

_DEBT = re.compile(r"D_c\s*=?\s*([0-9]+\.[0-9]+)")


def _question_default(tree: str) -> Decimal:
    document = yaml.safe_load((EXAMPLES / tree / "artifacts" / "question.yaml").read_text(encoding="utf-8"))
    found = [value for value in _walk(document, "debt_tolerance")]
    assert len(found) == 1, f"{tree}'s question declares debt_tolerance {len(found)} times"
    return Decimal(str(found[0]))


def _walk(node: object, key: str):  # noqa: ANN202
    if isinstance(node, dict):
        for name, value in node.items():
            if name == key:
                yield value
            else:
                yield from _walk(value, key)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value, key)


def _argparse_default(tree: str, flag: str) -> Decimal:
    """The default ``run.py`` declares for ``flag`` — read from its source, never restated here."""
    module = ast.parse((EXAMPLES / tree / "run.py").read_text(encoding="utf-8"))
    for node in ast.walk(module):
        if (
            isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "add_argument"
            and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == flag
        ):
            for keyword in node.keywords:
                if keyword.arg == "default" and isinstance(keyword.value, ast.Constant):
                    return Decimal(str(keyword.value.value))
    raise AssertionError(f"{tree}/run.py declares no default for {flag}")


@dataclass(frozen=True)
class Calibration:
    tree: str
    estate: tuple[str, ...]
    illustrative: Decimal
    #: Arguments that select the calibrated question (beyond the tolerance).
    arguments: tuple[str, ...] = ()
    #: Whether the illustrative value is the program's own default (asked with no flag).
    is_default: bool = True


CALIBRATIONS = (
    Calibration("cp-01-counterparty-reference-snapshot", ("CCF_CP_01_POSTGRES_DSN",),
                _question_default("cp-01-counterparty-reference-snapshot")),
    Calibration("cp-02-facility-terms-snapshot", ("CCF_CP_02_POSTGRES_DSN",), Decimal("0.65"),
                ("--facility", str(yaml.safe_load((EXAMPLES / "cp-02-facility-terms-snapshot" / "artifacts" / "expected.yaml").read_text(encoding="utf-8"))["declaration"]["fixtures"]["null_maturity"])),
                is_default=False),
    Calibration("cp-03-obligor-financial-spread", ("CCF_CP_03_POSTGRES_DSN",),
                _question_default("cp-03-obligor-financial-spread")),
    Calibration("cp-03-canonical-obligor-financial-spread", ("CCF_CP_03C_POSTGRES_DSN", "CCF_CP_03C_POSTGRES_SCHEMA"),
                _argparse_default("cp-03-canonical-obligor-financial-spread", "--debt-tolerance")),
)


def _run(calibration: Calibration, tolerance: Decimal | None) -> subprocess.CompletedProcess[str]:
    missing = [name for name in calibration.estate if not os.environ.get(name)]
    if missing:
        message = f"the live estate is not configured: {', '.join(missing)} unset (CLAUDE.md §9)"
        if os.environ.get("CCF_REQUIRE_ESTATE"):
            pytest.fail(message)
        pytest.skip(message)
    tree = EXAMPLES / calibration.tree
    flag = () if tolerance is None else ("--debt-tolerance", str(tolerance))
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(str(REPO_ROOT / part) for part in ("src", "runtime")) + os.pathsep + str(tree)}
    return subprocess.run(
        [sys.executable, "-B", str(tree / "run.py"), *calibration.arguments, *flag],
        capture_output=True, text=True, env=env, cwd=REPO_ROOT, timeout=600,
    )


def test_every_illustrative_value_is_above_the_original_and_labelled() -> None:
    """The four values are what the amendment says, and each artifact that declares one
    carries the illustrative-calibration disclosure where a reader meets it."""
    for calibration in CALIBRATIONS:
        assert calibration.illustrative > ORIGINAL, calibration
    for tree in ("cp-01-counterparty-reference-snapshot", "cp-03-obligor-financial-spread"):
        text = (EXAMPLES / tree / "artifacts" / "question.yaml").read_text(encoding="utf-8")
        assert "ILLUSTRATIVE CALIBRATION" in text and "not a recommended production value" in text, tree


@pytest.mark.parametrize("calibration", CALIBRATIONS, ids=lambda c: c.tree)
def test_the_illustrative_value_serves_and_the_original_value_refuses(calibration: Calibration) -> None:
    served = _run(calibration, None if calibration.is_default else calibration.illustrative)
    assert served.returncode == 0, served.stdout[-1500:] + served.stderr[-1500:]
    readings = _DEBT.findall(served.stdout)
    assert readings, f"{calibration.tree} served but printed no Context Debt:\n{served.stdout[-1500:]}"
    debt = Decimal(readings[0])
    # WHY the two outcomes differ: the measured debt lies between the two values.
    assert ORIGINAL < debt <= calibration.illustrative, (calibration.tree, debt)

    refused = _run(calibration, ORIGINAL)
    assert refused.returncode != 0, f"{calibration.tree} served at the original {ORIGINAL}:\n{refused.stdout[-1500:]}"
    text = refused.stdout + refused.stderr
    assert "tolerance-exceeded" in text, text[-1500:]
    assert "replay" in text and "ccf-artifact://" in text, text[-1500:]


# --- the declared demonstration serve instant, both outcomes ----------------------------
#
# cp-00, cp-01 and cp-02 declared a labelled `demonstration_serve_instant:` at their
# dated question's own instant on 2026-10-11 (ruling 1; `examples/AMENDMENTS-2026-10-11.md`)
# and had no ordinary test of the other outcome. The realistic deployment value is the
# REAL clock: the same documented default question, against a test-owned copy of the
# deployment's `ccf_config.yaml` with only that section removed, is refused
# `asked-at-outside-temporal-bound`. The served outcome is the documented default itself.

DEMONSTRATION_CLOCK = (
    Calibration("cp-00-institutional-holders", ("CCF_CP_00_POSTGRES_DSN",), Decimal("1")),
    Calibration("cp-01-counterparty-reference-snapshot", ("CCF_CP_01_POSTGRES_DSN",), Decimal("1")),
    Calibration("cp-02-facility-terms-snapshot", ("CCF_CP_02_POSTGRES_DSN",), Decimal("1")),
)

#: The line a served run prints — the label and a 64-hex address — never the prose a
#: specification page may print around it.
_SERVED_ADDRESS = re.compile(r"content address\s+[0-9a-f]{64}")

_DRIVER = """
import pathlib, sys
tree, config = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
sys.path.insert(0, str(tree))
import deployment
deployment.CONFIG = config          # the deployer's document: the tree's own, or a test-owned copy
sys.argv = [str(tree / "run.py")]
import run
raise SystemExit(run.main())
"""


def _run_on(calibration: Calibration, config: pathlib.Path) -> subprocess.CompletedProcess[str]:
    missing = [name for name in calibration.estate if not os.environ.get(name)]
    if missing:
        message = f"the live estate is not configured: {', '.join(missing)} unset (CLAUDE.md §9)"
        if os.environ.get("CCF_REQUIRE_ESTATE"):
            pytest.fail(message)
        pytest.skip(message)
    tree = EXAMPLES / calibration.tree
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(str(REPO_ROOT / part) for part in ("src", "runtime"))}
    return subprocess.run(
        [sys.executable, "-B", "-c", _DRIVER, str(tree), str(config)],
        capture_output=True, text=True, env=env, cwd=REPO_ROOT, timeout=600,
    )


@pytest.mark.parametrize("calibration", DEMONSTRATION_CLOCK, ids=lambda c: c.tree)
def test_the_demonstration_instant_serves_and_the_real_clock_refuses(
    calibration: Calibration, tmp_path: pathlib.Path
) -> None:
    from tests.examples.demonstration_deployment import deployment_on_the_real_clock  # noqa: PLC0415

    shipped = EXAMPLES / calibration.tree / "ccf_config.yaml"
    assert "demonstration_serve_instant:" in shipped.read_text(encoding="utf-8").splitlines()
    served = _run_on(calibration, shipped)
    assert served.returncode == 0, served.stdout[-1500:] + served.stderr[-1500:]
    assert _SERVED_ADDRESS.search(served.stdout), served.stdout[-1500:]

    real_clock = deployment_on_the_real_clock(shipped, directory=tmp_path / "deployment")
    refused = _run_on(calibration, real_clock)
    text = refused.stdout + refused.stderr
    assert refused.returncode != 0, f"{calibration.tree} served its dated question on the real clock:\n{text[-1500:]}"
    assert "asked-at-outside-temporal-bound" in text, text[-1500:]
    assert not _SERVED_ADDRESS.search(refused.stdout), "a refused run printed a served content address"
