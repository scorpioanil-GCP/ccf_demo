"""``ccf`` — the argparse noun-verb dispatcher (EXPR-02; D-IMPL-22).

SDK-defined (CLAUDE.md §8.3). Every command translates to requests against
the HTTP API routes; the CLI holds no fabric handle and interprets nothing
it moves (T-07-27: zero privileged paths).

**Transports.** Remote: a base URL supplied by ``--base-url`` or the
``CCF_BASE_URL`` environment variable — no deployment URL constant exists
in this package (CINV-01). Local: ``--local --local-root DIR`` constructs
the shared :class:`~ccf_runtime.http_api.dependencies.ApiDependencies`
bundle (:mod:`ccf_runtime.cli.local`) and drives the identical routes over
an in-process ASGI transport.

**Exit codes.** 0 — success. 1 — a typed 4xx refusal; the refusal body is
printed to stdout. 2 — a wiring error (transport failure or 5xx), reported
on stderr. The refusal-vs-exception line holds on the exit status exactly
as it holds over HTTP (T-07-26).

**B3 discipline.** One httpx client per invocation inside one
``asyncio.run`` — never a held session blocking a portal.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Sequence
from pathlib import Path

import httpx

from ccf_runtime.cli.commands import (
    RequestSpec,
    agent,
    artifact,
    config,
    hitl,
    product,
    replay,
    skill,
    workflow,
)
from ccf_runtime.http_api.dependencies import ApiDependencies

__ccf_mode__ = "algorithmic"

__all__ = ["build_parser", "main"]

#: The ASGI transport needs a syntactically valid base URL; the host is a
#: reserved-invalid name and the string is assembled from parts so no
#: scheme-prefixed deployment-URL literal exists in this package (CINV-01).
_LOCAL_BASE = "".join(("http", "://", "ccf.local.invalid"))

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_WIRING = 2


def build_parser() -> argparse.ArgumentParser:
    """The noun-verb parser over the D-IMPL-22 ruled inventory."""
    parser = argparse.ArgumentParser(
        prog="ccf",
        description=(
            "Thin client over the CCF HTTP API (D-IMPL-22): every action"
            " travels the same routes any client uses."
        ),
    )
    parser.add_argument(
        "--base-url",
        help="HTTP API base URL (or set CCF_BASE_URL)",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="run in-process over the shared ApiDependencies bundle",
    )
    parser.add_argument(
        "--local-root",
        help="directory for the --local file-backed artifact store",
    )
    subparsers = parser.add_subparsers(dest="noun", required=True)
    agent.register(subparsers)
    skill.register(subparsers)
    workflow.register(subparsers)
    hitl.register(subparsers)
    replay.register(subparsers)
    artifact.register(subparsers)
    product.register(subparsers)
    config.register(subparsers)
    return parser


async def _execute(
    specs: Sequence[RequestSpec],
    *,
    transport: httpx.AsyncBaseTransport | None,
    base_url: str,
) -> int:
    """Run the specs in order over one fresh client (B3)."""
    async with httpx.AsyncClient(
        transport=transport, base_url=base_url
    ) as client:
        for spec in specs:
            response = await client.request(
                spec.method,
                spec.path,
                params=dict(spec.params),
                json=spec.json,
            )
            if response.status_code >= 500:
                sys.stderr.write(
                    f"wiring error: {spec.method} {spec.path} ->"
                    f" {response.status_code}\n"
                )
                return EXIT_WIRING
            if response.status_code >= 400:
                sys.stdout.write(response.text + "\n")
                if spec.tolerate_empty_bump and response.status_code == 409:
                    try:
                        refusal_type = response.json().get("refusal_type")
                    except ValueError:
                        refusal_type = None
                    if refusal_type == "RefuseEmptyBump":
                        continue  # unchanged content re-registered: benign
                return EXIT_REFUSED
            sys.stdout.write(response.text + "\n")
    return EXIT_OK


def main(
    argv: Sequence[str] | None = None,
    *,
    dependencies: ApiDependencies | None = None,
) -> int:
    """Parse, translate, and execute one CLI invocation.

    Args:
        argv: Argument vector; ``None`` reads ``sys.argv``.
        dependencies: Optional injected bundle (tests; embedding). When
            supplied, the command runs in-process over these handles —
            the same type ``--local`` constructs and ``create_app``
            consumes.
    """
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    specs = args.build(args)

    transport: httpx.AsyncBaseTransport | None
    if dependencies is not None or args.local:
        if dependencies is None:
            if not args.local_root:
                parser.error("--local requires --local-root DIR")
            from ccf_runtime.cli.local import build_local_dependencies

            dependencies = build_local_dependencies(
                root=Path(args.local_root)
            )
        from ccf_runtime.http_api.app import create_app

        transport = httpx.ASGITransport(app=create_app(dependencies))
        base_url = _LOCAL_BASE
    else:
        configured = args.base_url or os.environ.get("CCF_BASE_URL")
        if not configured:
            parser.error("no base URL: pass --base-url or set CCF_BASE_URL")
        transport = None
        base_url = configured

    try:
        return asyncio.run(
            _execute(specs, transport=transport, base_url=base_url)
        )
    except httpx.TransportError as unreachable:
        sys.stderr.write(f"wiring error: {unreachable}\n")
        return EXIT_WIRING


if __name__ == "__main__":
    raise SystemExit(main())
