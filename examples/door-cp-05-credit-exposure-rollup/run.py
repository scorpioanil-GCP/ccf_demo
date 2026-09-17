"""Boot the door over frozen cp-05 and announce where it listens.

[ADAPT] freely — this file is presentation and nothing else. To ASK the
product in-process, use the frozen specimen's own ``run.py``; this tree exists
to reach it from another process::

    export CCF_CP_05_FLUREE_URL=...    CCF_CP_05_FLUREE_LEDGER=fibo-v2
    export CCF_CP_05_POSTGRES_DSN=...  CCF_CP_05_POSTGRES_SCHEMA=ccf_v2
    .venv/bin/python examples/door-cp-05-credit-exposure-rollup/run.py --door
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--door", action="store_true",
        help="boot the MCP egress door on an ephemeral 127.0.0.1 port, print `READY {port}`,"
             " and serve questions from other processes until terminated",
    )
    parsed = parser.parse_args(argv)
    if not parsed.door:
        parser.error("this tree is a door; pass --door (ask in-process through examples/cp-05-credit-exposure-rollup/run.py)")
    from server import serve as door  # noqa: PLC0415

    door.loopback(announce=lambda port: print(f"READY {port}", flush=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
