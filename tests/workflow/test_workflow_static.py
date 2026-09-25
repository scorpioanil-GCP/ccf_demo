"""The static tooth at the workflow surface, measured (D-IMPL-353 §1.4/§1.5b).

Runs mypy --strict on ``static_controls/wrong_kind_workflow.py`` — a
committed file with NO type-ignore and no cast — against the REAL
``WorkflowEngine.execute``/``resume`` and ``WorkflowFactory.construct``
signatures, and asserts: each wrong-kind call is reported as an incompatible
argument naming both kinds, and the handler that passes no capability is a
missing-argument error. The runtime half of the same claims lives in
``test_tenant_is_the_capabilitys.py``; the two teeth are two, and severing
``verify`` from the engine reddens that file while this one stays green.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

CONTROL = Path(__file__).parent / "static_controls" / "wrong_kind_workflow.py"
REPO = Path(__file__).resolve().parents[2]


def _mypy(path: Path) -> str:
    """mypy the way ``make typecheck`` runs it — full env, source roots on
    MYPYPATH so ``ccf``/``ccf_runtime`` resolve to the tree, not to an
    editable install without ``py.typed`` (the blind-instrument failure
    ``tests/authz/test_capability_static.py`` records)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = "src:runtime"
    env["MYPYPATH"] = "src:runtime"
    proc = subprocess.run(
        [sys.executable, "-m", "mypy", "--strict", "--no-error-summary", str(path)],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout + proc.stderr


def _marked(tag: str) -> set[int]:
    return {
        i + 1
        for i, line in enumerate(CONTROL.read_text().splitlines())
        if f"# {tag}-" in line
    }


def test_the_control_carries_no_suppression() -> None:
    text = CONTROL.read_text()
    assert "type: ignore" not in text
    assert "cast(" not in text


def test_every_wrong_kind_call_is_an_incompatible_argument() -> None:
    out = _mypy(CONTROL)
    marked = _marked("WRONG-KIND")
    assert len(marked) == 3
    reported = {
        int(m.group(1))
        for m in re.finditer(
            rf"{re.escape(CONTROL.name)}:(\d+): error: Argument 1", out
        )
    }
    missing = marked - reported
    assert not missing, f"the static tooth did not fire on lines {sorted(missing)}:\n{out}"
    assert "Authorized[Execute]" in out and "Authorized[Resume]" in out
    assert "Authorized[ArtifactRead]" in out


def test_a_handler_with_no_capability_does_not_type_check() -> None:
    """§1.4 verbatim: reaching ``construct`` with nothing to pass is a
    ``mypy --strict`` error, not a runtime surprise."""
    out = _mypy(CONTROL)
    (line,) = _marked("NO-CAPABILITY")
    pattern = rf"{re.escape(CONTROL.name)}:{line}: error: Missing positional argument \"authorized\""
    assert re.search(pattern, out), out
