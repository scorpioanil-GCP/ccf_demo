"""The static tooth at the governed dereference: mypy --strict rejects a wrong-kind capability.

D-IMPL-353 §1.5(b) for ``govern_dereference``, whose first parameter is
``Authorized[ArtifactRead] | Authorized[ReplayRead]``. Runs mypy on
``static_controls/wrong_kind_dereference.py`` — the two right kinds must be
clean, the two wrong kinds must be reported as incompatible arguments — with
the same runner ``tests/authz/test_capability_static.py`` uses, so a blind
instrument here would be blind there too and that file's positive control
would say so.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.authz.test_capability_static import _mypy

CONTROL = Path(__file__).parent / "static_controls" / "wrong_kind_dereference.py"


def test_the_control_carries_no_suppression() -> None:
    text = CONTROL.read_text()
    assert "type: ignore" not in text
    assert "cast(" not in text


def test_the_wrong_kinds_are_incompatible_and_the_right_kinds_are_clean() -> None:
    out = _mypy(CONTROL)
    lines = CONTROL.read_text().splitlines()
    marked = {i + 1 for i, line in enumerate(lines) if "# WRONG-KIND-" in line}
    assert len(marked) == 2
    reported = {
        int(m.group(1))
        for m in re.finditer(rf"{re.escape(CONTROL.name)}:(\d+): error: Argument 1", out)
    }
    assert marked <= reported, f"the static tooth did not fire on {sorted(marked - reported)}:\n{out}"
    assert reported <= marked, f"the right kinds were reported:\n{out}"
    assert "Authorized[ArtifactWrite]" in out and "Authorized[ProductRetrieve]" in out
