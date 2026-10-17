# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""SEC-020 Parts 1 and 3 through the bank's own door — `CSCC-G25` (Dave, 2026-10-16 21:32 GO).

The instance is launched by `packaging/bank-controlled/launch.sh` itself, unmodified, over this tree's committed
state (the launcher refuses a modified tree), with a closed environment, a private instance root and a fresh
bearer credential. Through it, an existing facility asked under another borrower's scope and an id that is not a
facility are asked on both routes a caller has — the product tool and the address-form template — and compared
by `packaging/bank-controlled/door_checks.py::compare`, which masks the replay digest and the echoed id only.
Then `verify.py` is run against the same instance, the door is stopped, and the retained evidence is asked
whether both questions became recorded decisions that replay.

**Reads the curated estate, seeds nothing** (CLAUDE.md §9): the door reads `.76` through its own read-only
settings; every write — the question stores, the replay store, the evidence index — lands in the instance root.
The credential file is deleted when the door stops.

Before the fix (measured 2026-10-16 on `5a3e9b9f`): the out-of-scope facility got a governed
`ttl-anchor-refusal`, the unknown one an opaque `ccf-runtime-failure` with no record — the existence oracle.
"""

from __future__ import annotations

import asyncio
import getpass
import importlib.util
import json
import os
import pathlib
import secrets
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any

import pytest
import yaml

pytestmark = [pytest.mark.fluree, pytest.mark.postgres]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
BANK = REPO_ROOT / "packaging" / "bank-controlled"
SERVE = REPO_ROOT / "examples" / "cp-06-canonical-collateral-and-setoff-coverage" / "server" / "serve.py"
QUESTION: dict[str, Any] = yaml.safe_load((BANK / "question.yaml").read_text(encoding="utf-8"))
PROBE = QUESTION["existence_probe"]
OUTSIDE, SCOPE = PROBE["outside_scope"]["facility_id"], list(PROBE["outside_scope"]["borrower_scope"])
UNKNOWN = PROBE["unknown_facility"]
ESTATE_VARIABLES = (
    "CCF_CP_06C_FLUREE_URL", "CCF_CP_06C_FLUREE_LEDGER",
    "CCF_CP_06C_POSTGRES_DSN", "CCF_CP_06C_POSTGRES_SCHEMA",
)
#: The three lines `verify.py` added for SEC-020; each must PASS on a fixed instance.
EXISTENCE_LINES = (
    "an unknown facility and one outside the requested scope get one answer (tool route)",
    "an unknown facility and one outside the requested scope get one answer (template route)",
    "both are recorded governed refusals with a replay reference, on both routes",
)


def _load_door_checks() -> Any:
    # By path: `packaging` is also the name of a PyPI distribution, which an import would resolve to instead.
    spec = importlib.util.spec_from_file_location("door_checks", BANK / "door_checks.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["door_checks"] = module
    spec.loader.exec_module(module)
    return module


dc = _load_door_checks()


@dataclass(frozen=True)
class Exchange:
    """Everything one launched instance answered, and what was left behind once it stopped."""

    root: pathlib.Path
    served: Any
    pairs: dict[str, tuple[Any, Any]]
    verify_rc: int
    verify_output: str


def _withheld(text: str) -> str:
    """The launcher's or verifier's output with the estate connection string removed, before any assertion shows it."""
    dsn = os.environ.get("CCF_CP_06C_POSTGRES_DSN")
    return text.replace(dsn, "<dsn>") if dsn else text


async def _ask_through_the_door(port: int, token: str) -> tuple[Any, dict[str, tuple[Any, Any]]]:
    from mcp import ClientSession  # noqa: PLC0415
    from mcp.client.streamable_http import streamablehttp_client  # noqa: PLC0415

    url = f"http://127.0.0.1:{port}/mcp"
    async with streamablehttp_client(url, headers={"Authorization": f"Bearer {token}"}) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            door = dc.Door(session, QUESTION)
            parameters = QUESTION["parameters"]
            served = await door.ask(parameters["facility_id"], list(parameters["borrower_scope"]))
            pairs = {
                "tool": (await door.ask(OUTSIDE, SCOPE), await door.ask(UNKNOWN, SCOPE)),
                "template": (await door.read(OUTSIDE, SCOPE), await door.read(UNKNOWN, SCOPE)),
            }
            return served, pairs


def _stopped(root: pathlib.Path) -> None:
    """`stop.sh`, then WAIT for the process to exit (the script does not), then delete the credential file."""
    pid = int((root / "run" / "pid").read_text())
    subprocess.run(["bash", str(BANK / "stop.sh"), str(root)], capture_output=True, text=True, timeout=60, check=False)
    deadline = time.monotonic() + 60
    while pathlib.Path(f"/proc/{pid}").exists() and time.monotonic() < deadline:
        time.sleep(0.2)
    (root / "secrets" / "instance.env").unlink(missing_ok=True)
    assert not pathlib.Path(f"/proc/{pid}").exists(), f"the door (pid {pid}) did not exit after stop.sh"


@pytest.fixture(scope="module")
def exchange(tmp_path_factory: pytest.TempPathFactory) -> Exchange:
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the curated estate is not configured: {', '.join(missing)} unset"
        if os.environ.get("CCF_REQUIRE_ESTATE"):
            pytest.fail(message)
        pytest.skip(message)
    root = tmp_path_factory.mktemp("bank-instance")
    root.chmod(0o700)
    (root / "secrets").mkdir(mode=0o700)
    credential = root / "secrets" / "instance.env"
    token = secrets.token_urlsafe(32)
    # SHELL-QUOTED: `launch.sh` reads this file with `source`, and an unquoted key/value DSN (it has spaces) is
    # silently cut at the first space — the door then refuses every question `source-unavailable`
    # (measured 2026-10-16, `sec020-measure/MEASUREMENT.md` item 2).
    lines = [f"CCF_SERVICE_ACCOUNT={shlex.quote(getpass.getuser())}", f"CCF_CP_06C_DOOR_TOKEN={token}",
             *(f"{name}={shlex.quote(os.environ[name])}" for name in ESTATE_VARIABLES)]
    credential.write_text("\n".join(lines) + "\n")
    credential.chmod(0o600)
    environment = {"PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", str(root)), "LANG": "C.UTF-8"}
    launched = subprocess.run(["bash", str(BANK / "launch.sh"), str(root), str(REPO_ROOT), sys.executable],
                              env=environment, capture_output=True, text=True, timeout=240, check=False)
    if launched.returncode != 0:
        credential.unlink(missing_ok=True)
        pytest.fail(f"launch.sh refused or the door did not start:\n{_withheld(launched.stderr)[-3000:]}")
    try:
        commit = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], capture_output=True, text=True,
                                check=True).stdout.strip()
        assert (root / "run" / "commit").read_text().strip() == commit, "the instance does not run the commit under test"
        port = int((root / "run" / "port").read_text())
        served, pairs = asyncio.run(_ask_through_the_door(port, token))
        verified = subprocess.run([sys.executable, "-B", str(BANK / "verify.py"), str(root), str(REPO_ROOT)],
                                  env=environment, capture_output=True, text=True, timeout=600, check=False)
    finally:
        _stopped(root)
    return Exchange(root=root, served=served, pairs=pairs, verify_rc=verified.returncode,
                    verify_output=_withheld(verified.stdout + verified.stderr))


def _served(answer: Any) -> bool:
    envelope = answer.envelope()
    return (answer.result is not None and answer.result.get("isError") is False and envelope is not None
            and envelope.get("refusal") is None and bool(envelope.get("content_address")))


def _precondition(exchange: Exchange) -> None:
    assert _served(exchange.served), (
        f"FAIL: precondition not met — the permitted question was not served, so {OUTSIDE}'s existence is"
        f" unproven: {(exchange.served.text() or exchange.served.error or '')[:300]}")


def test_a_permitted_request_still_serves_through_the_bank_door(exchange: Exchange) -> None:
    """The control (SEC-020 Parts 1-3, C1): the bank's own question — the probe facility under its own
    borrower — is served, with a content address and a replay reference, before and after the fix. It is also
    what proves the probe facility exists."""
    _precondition(exchange)
    envelope = exchange.served.envelope()
    assert envelope is not None and dc.REPLAY_REFERENCE.fullmatch(envelope["replay_ref"])


@pytest.mark.parametrize("route", ["tool", "template"])
def test_an_unknown_facility_and_one_outside_the_requested_scope_get_one_answer_through_the_bank_door(
    exchange: Exchange, route: str
) -> None:
    """Byte for byte, after masking only the fresh replay digest and the echoed facility id: an existing facility
    asked under another borrower's scope and an id that is not a facility get ONE answer, on the product tool and
    on the address-form template, through the instance `launch.sh` starts. Both are governed refusals.

    Declared product gate `CSCC-G25` (`CP-SPEC-006C` §G.1).
    """
    _precondition(exchange)
    outside, unknown = exchange.pairs[route]
    verdict = dc.compare(outside, unknown)
    assert verdict.ok, verdict.line()
    assert dc.is_governed_refusal(outside) and dc.is_governed_refusal(unknown), "identical, but not governed refusals"


def _inspect(root: pathlib.Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """`serve.py <verb>` over the stopped instance's evidence: no source setting, no credential, no new question."""
    environment = {"PATH": "/usr/bin:/bin", "HOME": str(root), "LANG": "C.UTF-8",
                   "CCF_REPLAY_EVIDENCE_ROOT": str(root / "evidence")}
    return subprocess.run([sys.executable, "-B", str(SERVE), *arguments], env=environment, capture_output=True,
                          text=True, timeout=300, check=False)


def test_both_answers_are_recorded_governed_refusals_that_replay(exchange: Exchange) -> None:
    """After the door stops, the retained evidence holds a finished decision for every probe question — the
    unknown facility included, which before the fix left only a pending marker and a traceback — each refused
    `subject-unavailable`, each reproduced by `serve.py replay`; no pending marker names either facility."""
    _precondition(exchange)
    for outside, unknown in exchange.pairs.values():
        for answer in (outside, unknown):
            envelope = answer.envelope()
            assert dc.is_governed_refusal(answer), f"{answer.route} {answer.facility_id}: not a governed refusal"
            assert envelope is not None and envelope["refusal"]["kind"] == "subject-unavailable", envelope
    listed = _inspect(exchange.root, "decisions", "--json")
    assert listed.returncode == 0, listed.stdout + listed.stderr
    entries = json.loads(listed.stdout)
    for facility in (OUTSIDE, UNKNOWN):
        mine = [entry for entry in entries if entry["subject"] == facility and entry["outcome"] != "served"]
        assert mine, f"no retained decision refuses {facility}"
        assert {entry["refusal_reason"] for entry in mine} == {"subject-unavailable"}, mine
        for entry in mine:
            replayed = _inspect(exchange.root, "replay", entry["record_address"])
            assert replayed.returncode == 0 and replayed.stdout.startswith("REPRODUCED"), replayed.stdout + replayed.stderr
    published = {entry["graph"] for entry in entries if entry.get("graph")}
    pending = [json.loads(path.read_text()) for path in (exchange.root / "evidence").glob("*-evidence-index/pending/*.json")]
    stranded = [marker["subject"] for marker in pending
                if marker["graph"] not in published and marker["subject"] in (OUTSIDE, UNKNOWN)]
    assert not stranded, f"questions began and never finished: {stranded}"


def test_verify_passes_with_the_existence_checks(exchange: Exchange) -> None:
    """`verify.py` — the bank's own check of a running instance — exits 0, and its three SEC-020 lines PASS."""
    _precondition(exchange)
    lines = exchange.verify_output.splitlines()
    for name in EXISTENCE_LINES:
        found = [line for line in lines if line[6:].startswith(name)]
        assert found and found[0].startswith("PASS"), f"{name}: {found or 'not reported'}"
    assert exchange.verify_rc == 0, exchange.verify_output[-3000:]
