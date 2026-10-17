# Copyright (c) 2026 David Castillo. All rights reserved.
"""Verify one running controlled bank instance: permissions, process environment, network exposure, authentication,
the exposed surface, one served answer, one refusal (Tuesday GO item 3, 2026-10-11), and that an unknown facility
cannot be told apart from an existing one outside the requested scope (SEC-020 Parts 1-3, 2026-10-16).

Usage: python verify.py <instance-root> <sdk-tree> [--timing] [--population <population.json>]
       (run as the service account; exits 1 on any FAIL)

``--timing`` adds the timing check (about 400 more questions, each leaving a permanent record in the instance's
evidence folder); ``--population`` adds the whole-population pair to it. The rule is in ``question.yaml`` ``timing:``.

These are deployment controls, not claims that the unrestricted SDK is fixed.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import pwd
import re
import stat
import sys
import traceback
import urllib.error
import urllib.request
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path

import yaml


def _arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("root", type=Path, help="the instance root")
    parser.add_argument("tree", type=Path, help="the SDK source tree the instance runs")
    parser.add_argument("--timing", action="store_true", help="also time unknown against existing facilities")
    parser.add_argument("--population", type=Path, help="a facility population file for the whole-population pair")
    return parser.parse_args(argv)


ARGS = _arguments(sys.argv[1:])
ROOT, TREE = ARGS.root, ARGS.tree
sys.path[:0] = [str(TREE / "src"), str(TREE / "runtime")]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
RESULTS: list[tuple[str, bool, str]] = []

#: The only environment names the door process may hold (launch.sh passes exactly these).
ALLOWED_ENV = {
    "PATH", "HOME", "LANG", "TMPDIR", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE",
    "CCF_CP_06C_DOOR_TOKEN", "CCF_CP_06C_FLUREE_URL", "CCF_CP_06C_FLUREE_LEDGER",
    "CCF_CP_06C_POSTGRES_DSN", "CCF_CP_06C_POSTGRES_SCHEMA",
    # D-IMPL-383: the private folder the door keeps every decision's replay evidence in.
    "CCF_REPLAY_EVIDENCE_ROOT",
}
#: Tool or resource names that would hand a caller an upload, storage-administration, audit or replay handle.
FORBIDDEN_SURFACE = re.compile(r"upload|artifact|admin|storage|audit|replay|grant|register|delete|write|put", re.I)
#: The inputs the timing rule is judged by; their hashes are printed with every timing run.
FROZEN_INPUTS = ("door_checks.py", "verify.py", "question.yaml")


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


def guarded(name: str, run: Callable[[], None]) -> None:
    """Run one group of checks; an exception is that group's FAIL, never the end of the report."""
    try:
        run()
    except Exception as error:  # noqa: BLE001 — every other check still runs
        check(name, False, f"could not be checked: {type(error).__name__}: {error}")


async def guarded_async(name: str, run: Callable[[], Awaitable[None]]) -> None:
    try:
        await run()
    except Exception as error:  # noqa: BLE001
        check(name, False, f"could not be checked: {type(error).__name__}: {error}")


def secrets() -> dict[str, str]:
    lines = (ROOT / "secrets" / "instance.env").read_text().splitlines()
    return dict(line.split("=", 1) for line in lines if "=" in line and not line.startswith("#"))


def permissions(account: str) -> None:
    uid = pwd.getpwnam(account).pw_uid
    for path, mode in ((ROOT, 0o700), (ROOT / "secrets" / "instance.env", 0o600),
                       (ROOT / "scratch", 0o700), (ROOT / "run", 0o700), (ROOT / "logs", 0o700),
                       (ROOT / "evidence", 0o700)):
        st = path.stat()
        check(f"permissions {path.relative_to(ROOT.parent)}",
              st.st_uid == uid and stat.S_IMODE(st.st_mode) == mode,
              f"owner uid {st.st_uid}, mode {oct(stat.S_IMODE(st.st_mode))}, want uid {uid} mode {oct(mode)}")
    for held in ("scratch", "evidence"):  # evidence: the retained replay evidence (D-IMPL-383)
        leaked = [str(p) for p in (ROOT / held).rglob("*") if stat.S_IMODE(p.stat().st_mode) & 0o077]
        check(f"{held} holds nothing readable by group or others", not leaked, ", ".join(leaked[:5]))


def process(pid: int, account: str) -> None:
    status = Path(f"/proc/{pid}/status").read_text()
    uid = int(re.search(r"^Uid:\s+(\d+)", status, re.M).group(1))
    check("door process runs as the service account, not root",
          uid == pwd.getpwnam(account).pw_uid and uid != 0, f"uid {uid}")
    names = {item.split(b"=", 1)[0].decode() for item in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0") if item}
    check("door environment holds only the allowlisted names", names <= ALLOWED_ENV, f"extra: {sorted(names - ALLOWED_ENV)}")


def listening(pid: int) -> list[str]:
    inodes = set()
    for fd in Path(f"/proc/{pid}/fd").iterdir():
        try:
            target = os.readlink(fd)
        except OSError:
            continue
        if target.startswith("socket:["):
            inodes.add(target[8:-1])
    found = []
    for table, width in (("tcp", 8), ("tcp6", 32)):
        for line in Path(f"/proc/net/{table}").read_text().splitlines()[1:]:
            cols = line.split()
            if cols[3] == "0A" and cols[9] in inodes:  # 0A = LISTEN
                hexaddr, hexport = cols[1].split(":")
                if width == 8:
                    addr = ".".join(str(int(hexaddr[i:i + 2], 16)) for i in (6, 4, 2, 0))
                else:
                    addr = "ipv6:" + hexaddr
                found.append(f"{addr}:{int(hexport, 16)}")
    return found


def exposure(pid: int, port: int) -> None:
    sockets = listening(pid)
    check("door listens on 127.0.0.1 only", bool(sockets) and all(s.startswith("127.0.0.1:") for s in sockets),
          ", ".join(sockets))
    check("the announced port is the listening port", f"127.0.0.1:{port}" in sockets)


def http_status(port: int, token: str | None) -> int:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "verify", "version": "0"}}}).encode()
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/mcp", body, headers), timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def existence(served: bool, pairs: dict) -> None:
    """SEC-020 Parts 1 and 3: an unknown facility and an existing one outside the requested scope get one answer."""
    from door_checks import compare, is_governed_refusal

    precondition = "precondition not met: the permitted question was not served, so the probe facility's existence is unproven"
    for route in ("tool", "template"):
        name = f"an unknown facility and one outside the requested scope get one answer ({route} route)"
        outside, unknown = pairs[route]
        if not served:
            check(name, False, precondition)
            continue
        verdict = compare(outside, unknown)
        if verdict.ok and not (is_governed_refusal(outside) and is_governed_refusal(unknown)):
            check(name, False, "precondition not met: the two answers match but are not governed refusals")
        else:
            check(name, verdict.ok, "identical after masking the replay digest and the echoed id" if verdict.ok
                  else verdict.line())
    answers = [answer for pair in pairs.values() for answer in pair]

    def kind(answer: object) -> str:
        envelope = answer.envelope()
        refusal = envelope.get("refusal") if envelope else None
        if isinstance(refusal, dict):
            return f"{refusal.get('kind')}/{refusal.get('reason')}"
        return answer.error or (answer.text() or "")[:80]

    name = "both are recorded governed refusals with a replay reference, on both routes"
    governed = all(is_governed_refusal(answer) for answer in answers)
    check(name, served and governed, precondition if not served else
          "; ".join(f"{a.route} {a.facility_id}: {kind(a)}" for a in answers))


async def surface_and_answer(port: int, token: str, question: dict) -> None:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.types import TextContent

    from door_checks import Door

    async with streamablehttp_client(f"http://127.0.0.1:{port}/mcp", headers={"Authorization": f"Bearer {token}"}) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            door = Door(session, question)
            served_ok = False

            async def surface() -> None:
                tools = [t.name for t in (await session.list_tools()).tools]
                check("exactly one tool, the read-only product request", tools == [door.tool], f"{tools}")
                resources = [str(x.uri) for x in (await session.list_resources()).resources]
                templates = [x.uriTemplate for x in (await session.list_resource_templates()).resourceTemplates]
                check("no upload, storage-administration, audit or replay handle is exposed",
                      not any(FORBIDDEN_SURFACE.search(n) for n in tools + resources + templates),
                      f"resources {resources}, templates {templates}")

            async def answer() -> None:
                nonlocal served_ok
                served = await session.call_tool(door.tool, door.arguments(question["tenant"], question["parameters"],
                                                                           question["subject"]))
                text = " ".join(c.text for c in served.content if isinstance(c, TextContent))
                ok, detail = False, text[:200]
                if not served.isError:
                    envelope = json.loads(text)
                    (ROOT / "run" / "served.json").write_text(text)
                    refusal = envelope.get("refusal")
                    ok = refusal is None and bool(envelope.get("content_address")) and bool(envelope.get("replay_ref"))
                    detail = (f"content address {envelope.get('content_address')}, replay {envelope.get('replay_ref')}"
                              if ok else f"governed refusal: {refusal.get('kind') if isinstance(refusal, dict) else refusal}"
                              f" / {refusal.get('reason') if isinstance(refusal, dict) else ''}: "
                              f"{refusal.get('detail') if isinstance(refusal, dict) else ''}")
                served_ok = ok
                check("the instance SERVES the question (an answer, not a refusal)", ok, detail)

            async def foreign() -> None:
                other = await session.call_tool(door.tool, door.arguments(question["foreign_tenant"],
                                                                          question["parameters"], question["subject"]))
                other_text = " ".join(c.text for c in other.content if isinstance(c, TextContent))
                check("a question for another tenant is refused", bool(other.isError), other_text[:160])

            async def probe() -> None:
                spec = question["existence_probe"]
                outside, scope = spec["outside_scope"]["facility_id"], list(spec["outside_scope"]["borrower_scope"])
                unknown = spec["unknown_facility"]
                print(f"ASSUMED  {unknown} is not a facility in this instance's estate"
                      " (verify.py cannot prove an absence)")
                pairs = {"tool": (await door.ask(outside, scope), await door.ask(unknown, scope)),
                         "template": (await door.read(outside, scope), await door.read(unknown, scope))}
                existence(served_ok, pairs)

            await guarded_async("the exposed surface", surface)
            await guarded_async("the instance SERVES the question (an answer, not a refusal)", answer)
            await guarded_async("a question for another tenant is refused", foreign)
            await guarded_async("an unknown facility and one outside the requested scope get one answer", probe)
            if ARGS.timing:
                await guarded_async("timing", lambda: timing(door, question))


async def timing(door: "Door", question: dict) -> None:  # noqa: F821 — door_checks.Door
    """SEC-020 Part 2: time existing-outside-scope against unknown, by the rule fixed in ``question.yaml``."""
    from door_checks import TimingRule, collect, judge_run

    rule = TimingRule.from_settings(question["timing"])
    spec = question["existence_probe"]
    outside, scope = spec["outside_scope"]["facility_id"], list(spec["outside_scope"]["borrower_scope"])
    unknown, second = spec["unknown_facility"], spec["control_unknown_facility"]
    pairs = {
        "T0": lambda i: ((unknown, scope), (second, scope)),
        "T1": lambda i: ((outside, scope), (unknown, scope)),
    }
    arms = {"T0": ("first", "second"), "T1": ("existing", "unknown"), "T2": ("existing", "unknown")}
    if ARGS.population is not None:
        population = json.loads(ARGS.population.read_text())
        within = question["timing"]["population_scope"]
        others = [facility for facility, borrower in population["facilities"] if borrower != within]
        absent = list(population["absent"])
        pairs["T2"] = lambda i: ((others[i % len(others)], [within]), (absent[i % len(absent)], [within]))
    hashes = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in FROZEN_INPUTS}
    print("TIMING inputs: " + ", ".join(f"{name} {digest[:16]}" for name, digest in hashes.items()))
    rows = await collect(door.ask, pairs, rule, arm_names=arms)
    judged = [name for name in ("T1", "T2") if name in pairs]
    run = judge_run(rows, rule, control="T0", judged=judged)
    out = ROOT / "run" / f"timing-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    out.write_text(json.dumps({"inputs": hashes, "rule": question["timing"],
                               "rows": [row.__dict__ for row in rows]}, indent=1))
    print(f"TIMING rows written to {out}")
    check("timing: the run is valid (the A/A control passes the rule; no failures)", run.valid,
          run.why_invalid or f"T0 {run.control.line()}")
    if not run.calibration_applies:
        print(f"NOTE  a control arm's interquartile range ({run.control_iqr_ms[0]:.1f}, {run.control_iqr_ms[1]:.1f} ms)"
              f" exceeds {rule.control_iqr_ceiling_ms:.0f} ms: the brief's resolution figures do not apply to this run")
    for name in judged:
        verdict = run.judged[name]
        check(f"timing {name}: an existing facility outside the scope takes as long as an unknown one",
              run.valid and verdict.passed, ("" if run.valid else "INVALID run: ") + verdict.line())
    mismatched = {name: found for name, found in run.signature_mismatches.items() if found}
    check("timing: every timed pair's two answers are identical (Part 1, all pairs)", not mismatched,
          "; ".join(f"{name}: {len(found)} pair(s), first {found[0]}" for name, found in mismatched.items()))


def main() -> int:
    values = secrets()
    account = values["CCF_SERVICE_ACCOUNT"]
    pid, port = int((ROOT / "run" / "pid").read_text()), int((ROOT / "run" / "port").read_text())
    token = values["CCF_CP_06C_DOOR_TOKEN"]
    question = yaml.safe_load((HERE / "question.yaml").read_text())
    print(f"instance {ROOT}  pid {pid}  port {port}  commit {(ROOT / 'run' / 'commit').read_text().strip()}")
    guarded("permissions", lambda: permissions(account))
    guarded("the door process", lambda: process(pid, account))
    guarded("network exposure", lambda: exposure(pid, port))
    guarded("no credential: refused with 401", lambda: check("no credential: refused with 401", http_status(port, None) == 401))
    guarded("a wrong credential: refused with 401",
            lambda: check("a wrong credential: refused with 401", http_status(port, "not-the-credential") == 401))
    try:
        asyncio.run(surface_and_answer(port, token, question))
    except Exception as error:  # noqa: BLE001 — a session that cannot be opened is a FAIL, reported
        check("the MCP session", False, f"could not be opened: {type(error).__name__}: {error}")
        traceback.print_exc()
    failed = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
