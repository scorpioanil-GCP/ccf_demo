# Copyright (c) 2026 David Castillo. All rights reserved.
"""Verify one running controlled bank instance: permissions, process environment, network exposure, authentication,
the exposed surface, one served answer, and one refusal (Tuesday GO item 3, 2026-10-11).

Usage: python verify.py <instance-root> <sdk-tree>   (run as the service account; exits 1 on any FAIL)

These are deployment controls, not claims that the unrestricted SDK is fixed.
"""

from __future__ import annotations

import asyncio
import json
import os
import pwd
import re
import stat
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT, TREE = Path(sys.argv[1]), Path(sys.argv[2])
sys.path[:0] = [str(TREE / "src"), str(TREE / "runtime")]
HERE = Path(__file__).resolve().parent
RESULTS: list[tuple[str, bool, str]] = []

#: The only environment names the door process may hold (launch.sh passes exactly these).
ALLOWED_ENV = {
    "PATH", "HOME", "LANG", "TMPDIR", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE",
    "CCF_CP_06C_DOOR_TOKEN", "CCF_CP_06C_FLUREE_URL", "CCF_CP_06C_FLUREE_LEDGER",
    "CCF_CP_06C_POSTGRES_DSN", "CCF_CP_06C_POSTGRES_SCHEMA",
}
#: Tool or resource names that would hand a caller an upload, storage-administration, audit or replay handle.
FORBIDDEN_SURFACE = re.compile(r"upload|artifact|admin|storage|audit|replay|grant|register|delete|write|put", re.I)


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


def secrets() -> dict[str, str]:
    lines = (ROOT / "secrets" / "instance.env").read_text().splitlines()
    return dict(line.split("=", 1) for line in lines if "=" in line and not line.startswith("#"))


def permissions(account: str) -> None:
    uid = pwd.getpwnam(account).pw_uid
    for path, mode in ((ROOT, 0o700), (ROOT / "secrets" / "instance.env", 0o600),
                       (ROOT / "scratch", 0o700), (ROOT / "run", 0o700), (ROOT / "logs", 0o700)):
        st = path.stat()
        check(f"permissions {path.relative_to(ROOT.parent)}",
              st.st_uid == uid and stat.S_IMODE(st.st_mode) == mode,
              f"owner uid {st.st_uid}, mode {oct(stat.S_IMODE(st.st_mode))}, want uid {uid} mode {oct(mode)}")
    leaked = [str(p) for p in (ROOT / "scratch").rglob("*") if stat.S_IMODE(p.stat().st_mode) & 0o077]
    check("scratch holds nothing readable by group or others", not leaked, ", ".join(leaked[:5]))


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


async def surface_and_answer(port: int, token: str, question: dict) -> None:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.types import TextContent

    from ccf.contracts.canonical import canonical_bytes
    from ccf.products.door import WireRequest
    from ccf_runtime.mcp.egress import PRODUCT_REQUEST_TOOL

    asked_at = (datetime.now(UTC).replace(microsecond=0) if question["asked_at"] == "now"
                else datetime.fromisoformat(question["asked_at"]))

    def arguments(tenant: str) -> dict:
        wire = WireRequest(product_id=question["product_class"], parameters=question["parameters"], temporal_boundary=asked_at)
        return {"tenant": tenant, "product_class": question["product_class"], "version": question["version"],
                "request": canonical_bytes(wire).decode("utf-8"), "subject": question["subject"],
                "intent": question["intent"], "freshness": question["freshness"],
                "asked_at": asked_at.isoformat(), "parameters": question["parameters"]}

    async with streamablehttp_client(f"http://127.0.0.1:{port}/mcp", headers={"Authorization": f"Bearer {token}"}) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            tools = [t.name for t in (await session.list_tools()).tools]
            check("exactly one tool, the read-only product request", tools == [PRODUCT_REQUEST_TOOL], f"{tools}")
            resources = [str(x.uri) for x in (await session.list_resources()).resources]
            templates = [x.uriTemplate for x in (await session.list_resource_templates()).resourceTemplates]
            check("no upload, storage-administration, audit or replay handle is exposed",
                  not any(FORBIDDEN_SURFACE.search(n) for n in tools + resources + templates),
                  f"resources {resources}, templates {templates}")
            served = await session.call_tool(PRODUCT_REQUEST_TOOL, arguments(question["tenant"]))
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
            check("the instance SERVES the question (an answer, not a refusal)", ok, detail)
            other = await session.call_tool(PRODUCT_REQUEST_TOOL, arguments(question["foreign_tenant"]))
            other_text = " ".join(c.text for c in other.content if isinstance(c, TextContent))
            check("a question for another tenant is refused", bool(other.isError), other_text[:160])


def main() -> int:
    values = secrets()
    account = values["CCF_SERVICE_ACCOUNT"]
    pid, port = int((ROOT / "run" / "pid").read_text()), int((ROOT / "run" / "port").read_text())
    token = values["CCF_CP_06C_DOOR_TOKEN"]
    question = yaml.safe_load((HERE / "question.yaml").read_text())
    print(f"instance {ROOT}  pid {pid}  port {port}  commit {(ROOT / 'run' / 'commit').read_text().strip()}")
    permissions(account)
    process(pid, account)
    exposure(pid, port)
    check("no credential: refused with 401", http_status(port, None) == 401)
    check("a wrong credential: refused with 401", http_status(port, "not-the-credential") == 401)
    asyncio.run(surface_and_answer(port, token, question))
    failed = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
