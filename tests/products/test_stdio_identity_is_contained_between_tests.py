"""A test that serves stdio in this pytest process leaves no ambient MCP identity behind for the tests after it.

Found by lane 378f-d3b (``D-IMPL-378``, 2026-10-08) and reproduced here.
``tests/products/test_paved_road.py::test_the_stdio_door_reads_neither_door_url_and_advertises_only_reserved_addresses``
calls ``ccf_runtime.mcp.product_door.ProductDoor.serve_stdio`` inside this process, with the transport stubbed.
``serve_stdio`` sets the MCP library's ``auth_context_var`` to the identity it is handed. By its documented contract,
stdio is single-principal: that one identity "answers for EVERY caller of the process". So a test that runs it
in-process, and does not contain what it sets, leaves the identity set for every later test in the process. A later
authorization test then runs as a stated stdio host identity rather than as the caller it builds, and can pass or
fail for the wrong reason.

``tests/mcp/test_stdio_door_identity.py`` already contains every call it makes (``auth_context_var.set(None)``, then
``reset`` in a ``finally``).

The probe reads the variable itself, never a downstream symptom. Run alone, it passes. The control runs the
paved-road stdio test and then the probe in ONE pytest process, and requires the probe to find nothing set.

Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

from mcp.server.auth.middleware.auth_context import auth_context_var

#: The repository root (this module sits at tests/products/).
_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The test that serves stdio in this process, with the transport stubbed.
_STDIO_TEST = (
    "tests/products/test_paved_road.py"
    "::test_the_stdio_door_reads_neither_door_url_and_advertises_only_reserved_addresses"
)

#: This module's probe.
_PROBE = f"{pathlib.Path(__file__).resolve().relative_to(_ROOT).as_posix()}::test_no_mcp_identity_is_ambient_when_this_test_starts"


def test_no_mcp_identity_is_ambient_when_this_test_starts() -> None:
    """The probe: no identity an earlier test set in this process is still the ambient MCP identity."""
    ambient = auth_context_var.get(None)
    token = getattr(ambient, "access_token", None)
    assert ambient is None, (
        "an earlier test in this process left an ambient MCP identity set:"
        f" {type(ambient).__name__} for client {getattr(token, 'client_id', None)!r},"
        f" scopes {getattr(token, 'scopes', None)!r}"
    )


def test_the_paved_road_stdio_test_leaves_no_ambient_identity_for_the_test_after_it(tmp_path: pathlib.Path) -> None:
    """The paved-road stdio test, then the probe, in one pytest process; the probe must find nothing set."""
    estate = ("PG", "FLUREE_", "MONGO_", "NEO4J_", "CO_LENDER_")
    environment = {key: value for key, value in os.environ.items() if not key.startswith(estate)}
    environment["PYTHONPATH"] = os.pathsep.join(str(_ROOT / part) for part in ("src", "runtime"))
    junit = tmp_path / "in-one-process.junit.xml"
    ran = subprocess.run(
        [
            sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-q",
            f"--junitxml={junit}", _STDIO_TEST, _PROBE,
        ],
        cwd=_ROOT, env=environment, capture_output=True, text=True, timeout=300, check=False,
    )
    assert junit.exists(), f"the one-process run produced no report: {ran.stdout[-2000:]}{ran.stderr[-2000:]}"
    cases = [(case.get("name"), case) for case in ET.parse(junit).getroot().iter("testcase")]
    assert [name for name, _case in cases] == [_STDIO_TEST.rpartition("::")[2], _PROBE.rpartition("::")[2]], (
        f"the run did not run the stdio test and then the probe, in that order: {[name for name, _ in cases]}"
    )

    def _verdict(case: ET.Element) -> str:
        for kind in ("failure", "error", "skipped"):
            found = case.find(kind)
            if found is not None:
                return f"{kind}: {found.get('message', '')}"
        return "passed"

    (_, stdio), (_, probe) = cases
    assert _verdict(stdio) == "passed", (
        f"the case was not constructed: the stdio test itself did not pass in this run: {_verdict(stdio)}"
    )
    assert _verdict(probe) == "passed", (
        "after the paved-road stdio test ran, an MCP identity was still ambient in the same process, so every later"
        f" test runs as it. The probe reported: {_verdict(probe)}"
    )
