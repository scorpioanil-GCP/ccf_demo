"""The static tooth, measured: mypy --strict rejects a wrong-kind capability.

D-IMPL-353 §1.5(b) and §9. Runs mypy on `static_controls/wrong_kind.py` — a
committed file with NO type-ignore — and asserts each of its four wrong-kind
calls is reported as an incompatible argument. Separate from the runtime
controls in `test_capability.py` on purpose: the two teeth are two, and §9's
severing "drop the kind check from verify" must redden the runtime half while
this file stays green.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

CONTROL = Path(__file__).parent / "static_controls" / "wrong_kind.py"
REPO = Path(__file__).resolve().parents[2]


def _mypy(path: Path) -> str:
    """Run mypy the way `make typecheck` does — same cwd, same PYTHONPATH,
    the FULL environment. A stripped env made the child resolve
    `ccf_runtime` through the editable install ("missing py.typed") instead
    of the source tree, which reported the static tooth as absent when it
    was the runner that was blind. The instrument has to be able to see
    before its silence means anything."""
    env = dict(os.environ)
    env["PYTHONPATH"] = "src:runtime"
    # mypy resolves IMPORTS through MYPYPATH, not PYTHONPATH. Without it,
    # an explicit-file run found `ccf_runtime` through the editable install,
    # saw no `py.typed`, treated every name as `Any`, and reported the static
    # tooth as absent — the instrument blind, not the tooth missing. `make
    # typecheck` never hits this because it passes no file and the pyproject
    # config supplies the source roots.
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


def test_every_wrong_kind_call_is_an_incompatible_argument() -> None:
    out = _mypy(CONTROL)
    lines = CONTROL.read_text().splitlines()
    marked = {
        i + 1
        for i, line in enumerate(lines)
        if "# WRONG-KIND-" in line
    }
    assert len(marked) == 4
    reported = {
        int(m.group(1))
        for m in re.finditer(rf"{re.escape(CONTROL.name)}:(\d+): error: Argument 1", out)
    }
    missing = marked - reported
    assert not missing, (
        f"the static tooth did not fire on lines {sorted(missing)}:\n{out}"
    )
    # and the diagnostic names the two kinds, so a reader sees WHY
    assert 'Authorized[ArtifactRead]' in out and 'Authorized[ArtifactWrite]' in out


def test_a_right_kind_call_type_checks_clean(tmp_path: Path) -> None:
    """The positive half: the same shape with the RIGHT kind is clean, so the
    negative result above is the kind, not the file."""
    ok = tmp_path / "right_kind.py"
    ok.write_text(
        "from ccf_runtime.authz.capability import ArtifactWrite, Authorized\n"
        "def artifact_put(authorized: Authorized[ArtifactWrite]) -> None: ...\n"
        "def writer(w: Authorized[ArtifactWrite]) -> None:\n"
        "    artifact_put(w)\n"
    )
    out = _mypy(ok)
    assert "error:" not in out, out


COMPOSITION_CONTROL = Path(__file__).parent / "static_controls" / "composition_kind.py"


def test_the_composition_control_carries_no_suppression() -> None:
    text = COMPOSITION_CONTROL.read_text()
    assert "type: ignore" not in text
    assert "cast(" not in text


def test_a_door_kind_at_composition_is_a_type_error_and_the_two_kinds_are_clean() -> None:
    """D-IMPL-354's static tooth: the overloads admit ReplayMint and Register
    only. Both marked lines are reported; the two composition-kind calls
    above them are not — the error is the kind, not the file."""
    out = _mypy(COMPOSITION_CONTROL)
    lines = COMPOSITION_CONTROL.read_text().splitlines()
    marked = {i + 1 for i, line in enumerate(lines) if "# COMPOSITION-KIND-" in line}
    assert len(marked) == 2
    reported = {
        int(m.group(1))
        for m in re.finditer(rf"{re.escape(COMPOSITION_CONTROL.name)}:(\d+): error:", out)
    }
    assert marked <= reported, f"the static tooth did not fire on {sorted(marked - reported)}:\n{out}"
    assert reported <= marked, f"unexpected errors:\n{out}"
