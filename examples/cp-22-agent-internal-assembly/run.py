"""Run both agents and show the boundary.

[ADAPT] freely — presentation only. Starts Agent B in its OWN OS PROCESS,
asks from Agent A in this one, and tears the peer down.

Usage::

    export CCF_CP_21_POSTGRES_DSN=...  CCF_CP_21_POSTGRES_SCHEMA=ccf_v2
    export CCF_CP_21_FLUREE_URL=...    CCF_CP_21_FLUREE_LEDGER=fibo-v2
    export CCF_CP_21_MONGO_URI=...     CCF_CP_21_MONGO_DB=fibo_v2
    export CCF_CP_21_TOKEN_CREDITOFFICER=... (and the other three)
    make -s example-cp-22

Agent B consumes `examples/cp-21-large-exposure`, so it reads THAT rung's
environment. CP-22 declares none of its own.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import yaml

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import agent_a  # noqa: E402

DECLARATION = yaml.safe_load(
    (HERE / "artifacts" / "agent-b.yaml").read_text(encoding="utf-8"))["declaration"]
QUESTION = yaml.safe_load(
    (HERE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]


def wait_for(base_url: str, *, seconds: float = 45.0) -> bool:
    """Poll the peer's agent card until it answers."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{base_url}/.well-known/agent-card.json", timeout=2.0).status_code == 200:
                return True
        except Exception:  # noqa: BLE001 — not up yet is the expected case
            pass
        time.sleep(0.5)
    return False


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", default=QUESTION["question"]["subject"])
    parser.add_argument("--instant", default=QUESTION["question"]["instant"])
    parser.add_argument("--port", type=int, default=DECLARATION["a2a"]["port"])
    parser.add_argument("--strict", action="store_true",
                        help="run the peer at its strict debt tolerance (AIA-G10)")
    parser.add_argument("--noise", action="store_true",
                        help="send fields the peer must ignore (AIA-G08)")
    arguments = parser.parse_args(argv)

    base_url = f"http://{DECLARATION['a2a']['host']}:{arguments.port}"
    command = [sys.executable, str(HERE / "agent_b.py"), "--port", str(arguments.port)]
    if arguments.strict:
        command.append("--strict")

    print(f"starting Agent B as a separate OS process on {base_url} ...")
    peer = subprocess.Popen(command)  # noqa: S603
    try:
        if not wait_for(base_url):
            print("Agent B did not come up")
            return 2
        print(f"Agent B is pid {peer.pid}; Agent A is pid {os.getpid()} — two processes, one socket\n")
        print(f"Agent A asks: subject={arguments.subject} instant={arguments.instant}"
              + ("  (+ fields the peer must ignore)" if arguments.noise else ""))
        return agent_a.main([
            "--base-url", base_url, "--subject", arguments.subject,
            "--instant", arguments.instant, *(["--noise"] if arguments.noise else []),
        ])
    finally:
        peer.terminate()
        try:
            peer.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            peer.kill()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
