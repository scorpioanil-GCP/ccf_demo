"""The CLI hands ``create_app`` a TYPED five-seam bundle; mypy checks it, no ignore.

D-IMPL-353 §4 rule 6 (``d353-authz-type-ignore``). The lint's seam roster named
the in-process leg of ``runtime/ccf_runtime/cli/main.py::main`` —
``create_app(dependencies, **authority)  # type: ignore[arg-type]`` over ``authority: Mapping[str, object] | None`` — the
authority seams as an untyped bag forced past the type checker, a shape this
remediation itself created when ``create_app``'s seams became required. The
repair is a ``TypedDict``, :class:`ccf_runtime.http_api.app.HttpAuthority`,
naming exactly the keyword seams ``create_app`` takes, so an embedder that
omits one is a mypy error at its own call site rather than a ``TypeError`` at
the CLI's.

Two teeth, as everywhere in D-IMPL-353: a runtime control that the bundle's
keys ARE ``create_app``'s keyword-only parameters with the same types (so the
two cannot drift apart), and a static control — a committed file carrying no
suppression — in which three incomplete bundles are each reported by
``mypy --strict`` on the marked line.
"""

from __future__ import annotations

import inspect
import os
import re
import subprocess
import sys
import typing
from pathlib import Path

CONTROL = Path(__file__).parent / "static_controls" / "missing_seam.py"
REPO = Path(__file__).resolve().parents[2]
CLI_MAIN = REPO / "runtime" / "ccf_runtime" / "cli" / "main.py"


def _mypy(path: Path) -> str:
    """Same runner as ``tests/authz/test_capability_static.py::_mypy``: full env,
    MYPYPATH so imports resolve to the source tree and not the editable
    install (which has no ``py.typed`` and would make every name ``Any``)."""
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


def test_the_bundle_names_exactly_create_apps_keyword_seams() -> None:
    from ccf_runtime.http_api.app import HttpAuthority, create_app

    seams = {
        name: parameter
        for name, parameter in inspect.signature(create_app).parameters.items()
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY
    }
    assert seams, "create_app has keyword-only seams"
    # Every seam is required on create_app (D-IMPL-353 §4 rule 1)...
    assert all(p.default is inspect.Parameter.empty for p in seams.values())
    # ...and the bundle names exactly those, all required, same types.
    assert set(HttpAuthority.__required_keys__) == set(seams)
    assert not HttpAuthority.__optional_keys__
    app_hints = typing.get_type_hints(create_app)
    bundle_hints = typing.get_type_hints(HttpAuthority)
    for name in seams:
        assert bundle_hints[name] == app_hints[name], name


def test_the_cli_carries_no_type_ignore_and_takes_the_bundle() -> None:
    text = CLI_MAIN.read_text()
    assert "type: ignore" not in text
    from ccf_runtime.cli.main import main

    annotation = inspect.signature(main).parameters["authority"].annotation
    # `from __future__ import annotations`: the annotation is its source text.
    assert annotation == "HttpAuthority | None", annotation


def test_the_control_carries_no_suppression() -> None:
    text = CONTROL.read_text()
    assert "type: ignore" not in text
    assert "cast(" not in text


def test_every_incomplete_bundle_is_reported_on_its_line() -> None:
    out = _mypy(CONTROL)
    lines = CONTROL.read_text().splitlines()
    marked = {i + 1 for i, line in enumerate(lines) if "# MISSING-SEAM-" in line}
    assert len(marked) == 3
    reported = {
        int(m.group(1))
        for m in re.finditer(rf"{re.escape(CONTROL.name)}:(\d+): error:", out)
    }
    missing = marked - reported
    assert not missing, f"mypy admitted the bundles on lines {sorted(missing)}:\n{out}"
    # And nothing ELSE in the control is an error — the instrument sees the
    # file, and the only errors are the three it was written to carry.
    assert reported <= marked, f"unexpected errors:\n{out}"
