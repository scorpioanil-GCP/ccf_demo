# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The two safety corrections in ``tests/examples/conftest.py`` hold (Dave, 2026-10-16 18:35, ruling 3).

*"Tests must not print the database password if the connection fails"* and
*"The test copy of the collateral service must not write its records into the
local evidence folder."* Held end to end on a frozen example's own test module,
``test_cp_14_third_slice.py``, which did both before the correction: it is run
in a subprocess with every estate variable pointed at a CLOSED loopback port
(nothing is contacted) and a marker password, and with the evidence-root
variable naming an empty folder.

* With the directory's shared configuration, the marker appears nowhere in the
  output and the folder stays empty.
* With ``--noconftest`` — the correction removed, and nothing else — the same
  run prints the marker and writes into the folder. That control proves the
  probe can see each leak, so the first result is not a probe that sees nothing.

Measured across every example test module on 2026-10-16, before the
correction: 28 printed a marker password, 4 wrote into the evidence folder.
"""

from __future__ import annotations

import ast
import os
import pathlib
import subprocess
import sys

import pytest

from tests.examples.conftest import EVIDENCE_ROOT_VARIABLE, withhold_credentials

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SUBJECT = "tests/examples/test_cp_14_third_slice.py"
SERVE = REPO_ROOT / "examples" / "cp-06-canonical-collateral-and-setoff-coverage" / "server" / "serve.py"

MARKER = "Mk7pwZQ9sentinel"
CLOSED = "127.0.0.1:9"
DSN_FORMS = {
    "uri": f"postgresql://u:{MARKER}@{CLOSED}/x?connect_timeout=1",
    "keywords": f"host=127.0.0.1 port=9 dbname=x user=u password={MARKER} connect_timeout=1",
}
#: The estate legs ``test_cp_14_third_slice.py`` reads, each pointed at the closed port.
LEGS = ("CP_03C", "CP_04C", "CP_06C", "CP_14")
FLUREE_LEGS = ("CP_04C", "CP_06C", "CP_14")


def _run(tmp_path: pathlib.Path, dsn: str, *extra: str) -> tuple[str, list[str]]:
    tmp_path.mkdir()
    evidence = tmp_path / "evidence"
    evidence.mkdir(mode=0o700)
    env = {"HOME": os.environ.get("HOME", str(tmp_path)), "PATH": "/usr/bin:/bin", "PYTHONPATH": ".:src:runtime",
           EVIDENCE_ROOT_VARIABLE: str(evidence)}
    for leg in LEGS:
        env[f"CCF_{leg}_POSTGRES_DSN"] = dsn
        env[f"CCF_{leg}_POSTGRES_SCHEMA"] = "ccf_v2"
    for leg in FLUREE_LEGS:
        env[f"CCF_{leg}_FLUREE_URL"] = f"http://{CLOSED}"
        env[f"CCF_{leg}_FLUREE_LEDGER"] = "fibo-v2"
    completed = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--basetemp={tmp_path / 'bt'}",
         *extra, SUBJECT],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=300,
    )
    return completed.stdout + completed.stderr, sorted(entry.name for entry in evidence.iterdir())


@pytest.mark.parametrize("form", sorted(DSN_FORMS))
def test_a_failed_estate_connection_prints_no_password_and_writes_no_evidence(tmp_path: pathlib.Path, form: str) -> None:
    output, written = _run(tmp_path / "corrected", DSN_FORMS[form])
    assert "error" in output or "failed" in output, f"the subject never reached a failed connection:\n{output[-1500:]}"
    assert MARKER not in output, f"a password was printed ({output.count(MARKER)} times)"
    assert written == [], f"a test's door wrote into the evidence folder: {written}"

    control, control_written = _run(tmp_path / "control", DSN_FORMS[form], "--noconftest")
    assert MARKER in control, "control: without the correction the probe saw no password — it cannot see the leak"
    assert control_written, "control: without the correction no door wrote evidence — the probe cannot see that leak"


def test_the_evidence_root_named_here_is_the_one_the_collateral_door_reads() -> None:
    for node in ast.parse(SERVE.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and [getattr(t, "id", None) for t in node.targets] == ["EVIDENCE_ROOT_VARIABLE"]:
            assert isinstance(node.value, ast.Constant)
            assert node.value.value == EVIDENCE_ROOT_VARIABLE
            return
    raise AssertionError(f"{SERVE} no longer assigns EVIDENCE_ROOT_VARIABLE")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("conninfo = 'user=u password=s3cret connect_timeout=1'", "conninfo = 'user=u password=<withheld> connect_timeout=1'"),
        ("dsn = 'postgresql://parkave:s3cret@192.0.2.1:5432/db'", "dsn = 'postgresql://parkave:<withheld>@192.0.2.1:5432/db'"),
        ("mongodb://reader:p%40ss@h1:27017,h2:27017/db", "mongodb://reader:<withheld>@h1:27017,h2:27017/db"),
        ("password = 'two words'", "password = <withheld>"),
        ("{'password': 's3cret', 'user': 'u'}", "{'password': <withheld>, 'user': 'u'}"),
        ("PGPASSWORD=s3cret make example", "PGPASSWORD=<withheld> make example"),
        # Already masked by another guard (estate_guard writes `***`), or a source
        # placeholder a traceback shows: left exactly as they are.
        ("postgresql://parkave:***@192.0.2.1:5432/db", "postgresql://parkave:***@192.0.2.1:5432/db"),
        ("password=*** host=h", "password=*** host=h"),
        ('f"postgresql://parkave:{secret}@{CURATED}"', 'f"postgresql://parkave:{secret}@{CURATED}"'),
        ("password={password!r}", "password={password!r}"),
        # Not credentials, and never rewritten: a URL with no userinfo, a later '@'.
        ("url = 'http://127.0.0.1:9/mcp'\n    @pytest.fixture", "url = 'http://127.0.0.1:9/mcp'\n    @pytest.fixture"),
        ("test_the_password_policy_refuses", "test_the_password_policy_refuses"),
    ],
)
def test_password_shapes_are_withheld_and_nothing_else(text: str, expected: str) -> None:
    assert withhold_credentials(text) == expected
