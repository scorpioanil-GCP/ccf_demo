"""The static tooth, measured on the ``src/`` handles: mypy --strict rejects a wrong-kind capability.

D-IMPL-353 §1.5(b) and §9, for Lane HANDLES' five handles. Runs mypy on
``static_controls/wrong_kind.py`` — a committed file with NO ``type: ignore``
and NO ``cast`` — and asserts each marked wrong-kind line is reported as an
incompatible argument, while the unmarked right-kind lines in the same file
report nothing. Same runner as ``tests/authz/test_capability_static.py``
(``MYPYPATH=src:runtime`` — mypy resolves imports through MYPYPATH, not
PYTHONPATH; without it the runner sees the editable install's ``ccf`` with
no ``py.typed`` and reports the tooth absent when it is the runner that is
blind).

Separate from the runtime controls on purpose: the two teeth are two, and a
severing that drops ``verify`` from a handle must redden the runtime control
while this file stays green.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

CONTROL = Path(__file__).parent / "static_controls" / "wrong_kind.py"
REPO = Path(__file__).resolve().parents[2]
MARKS = 11


def _mypy(path: Path) -> str:
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


def test_the_control_carries_no_suppression() -> None:
    text = CONTROL.read_text()
    assert "type: ignore" not in text
    assert "cast(" not in text


def test_every_wrong_kind_call_is_an_incompatible_argument_and_nothing_else_is() -> None:
    out = _mypy(CONTROL)
    lines = CONTROL.read_text().splitlines()
    marked = {i + 1 for i, line in enumerate(lines) if "# WRONG-KIND-" in line}
    assert len(marked) == MARKS, sorted(marked)
    reported = {
        int(m.group(1))
        for m in re.finditer(rf"{re.escape(CONTROL.name)}:(\d+): error: Argument", out)
    }
    missing = marked - reported
    assert not missing, f"the static tooth did not fire on lines {sorted(missing)}:\n{out}"
    # The positive half: every diagnostic mypy raised is on a marked line —
    # the right-kind calls in the same file are clean, so the reds are the kind.
    all_reported = {
        int(m.group(1))
        for m in re.finditer(rf"{re.escape(CONTROL.name)}:(\d+): error:", out)
    }
    # `artifact_class=None` on lines 2-3 also draws its own arg-type error; that
    # is on a marked line and is not a wrong-kind finding, so it is tolerated
    # there and nowhere else.
    stray = all_reported - marked
    assert not stray, f"diagnostics on unmarked lines {sorted(stray)}:\n{out}"
    assert "Authorized[ArtifactRead]" in out
