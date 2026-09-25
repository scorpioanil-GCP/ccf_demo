"""The static tooth at the HITL transport handle, measured (D-IMPL-353 §1.5b, §9).

Mirrors ``tests/authz/test_capability_static.py`` for the two handles this
lane owns: ``mypy --strict`` must report an incompatible argument where a
``Authorized[HitlQueueRead]`` reaches ``submit`` and where an
``Authorized[HitlSubmit]`` reaches ``view``. Separate from the runtime controls
in ``test_transport_capability.py`` on purpose — the two teeth are two.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

CONTROL = Path(__file__).parent / "static_controls" / "wrong_kind_hitl.py"
REPO = Path(__file__).resolve().parents[2]


def _mypy(path: Path) -> str:
    """Run mypy as ``make typecheck`` does, with the source roots on
    ``MYPYPATH`` — an explicit-file run without it resolves ``ccf_runtime``
    through the editable install and reports the tooth absent when it is the
    runner that is blind (the lesson recorded in ``tests/authz``)."""
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


def test_every_wrong_kind_call_is_an_incompatible_argument() -> None:
    out = _mypy(CONTROL)
    lines = CONTROL.read_text().splitlines()
    marked = {i + 1 for i, line in enumerate(lines) if "# WRONG-KIND-" in line}
    assert len(marked) == 2
    reported = {
        int(m.group(1))
        for m in re.finditer(
            rf"{re.escape(CONTROL.name)}:(\d+): error: Argument 1", out
        )
    }
    missing = marked - reported
    assert not missing, f"the static tooth did not fire on lines {sorted(missing)}:\n{out}"
    assert "Authorized[HitlQueueRead]" in out and "Authorized[HitlSubmit]" in out


def test_a_right_kind_call_type_checks_clean(tmp_path: Path) -> None:
    ok = tmp_path / "right_kind_hitl.py"
    ok.write_text(
        "from ccf.hitl.transport import HitlActionSubmission, InMemoryHitlTransport\n"
        "from ccf.authz.capability import Authorized, HitlQueueRead, HitlSubmit\n"
        "def submitter(t: InMemoryHitlTransport, a: Authorized[HitlSubmit],"
        " s: HitlActionSubmission) -> HitlActionSubmission:\n"
        "    return t.submit(a, submission=s)\n"
        "def reader(t: InMemoryHitlTransport, a: Authorized[HitlQueueRead]) -> int:\n"
        "    return len(t.view(a))\n"
    )
    out = _mypy(ok)
    assert "error:" not in out, out
