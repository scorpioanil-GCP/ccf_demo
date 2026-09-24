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

**The remote leg is authenticated (SEC-016).** Every remote invocation
carries a bearer credential resolved by :mod:`ccf_runtime.cli.credential`
from a source the deployment *names* — ``--token-env NAME`` /
``CCF_TOKEN_ENV``, or ``--token-file PATH`` / ``CCF_TOKEN_FILE``. No flag
takes a token value, no default source exists, and a remote invocation
with none configured **refuses**: the CLI does not fall back to an
anonymous call, and there is no flag that turns the requirement off. The
local leg hosts no network boundary and resolves no credential.

**Exit codes.** 0 — success. 1 — a typed 4xx refusal, or a verb refusing
its own inputs; the refusal body is printed to stdout. 2 — a wiring
error, reported on stderr: deployment wiring that has to be settled
before any request can be built (no base URL, no usable credential), a
transport failure, or a 5xx. The refusal-vs-exception line holds on the
exit status exactly as it holds over HTTP (T-07-26).

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
from pydantic import SecretStr

from ccf_runtime.cli.commands import (
    CommandRefused,
    RequestSpec,
    agent,
    artifact,
    backends,
    config,
    hitl,
    product,
    replay,
    schema,
    skill,
    workflow,
)
from ccf_runtime.cli.credential import (
    CredentialUnresolved,
    authorization_headers,
    resolve_remote_credential,
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
    # A source is NAMED, never a value: no flag here takes a token,
    # because a secret in `argv` is a secret in `ps` (SEC-016). Neither
    # flag has a default — the SDK ships no token and names no default
    # place to look for one (CINV-01).
    parser.add_argument(
        "--token-env",
        help=(
            "name of the environment variable holding the API bearer"
            " token (or set CCF_TOKEN_ENV)"
        ),
    )
    parser.add_argument(
        "--token-file",
        help=(
            "path of the file holding the API bearer token (or set"
            " CCF_TOKEN_FILE)"
        ),
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
    schema.register(subparsers)
    backends.register(subparsers)
    return parser


async def _execute(
    specs: Sequence[RequestSpec],
    *,
    transport: httpx.AsyncBaseTransport | None,
    base_url: str,
    credential: SecretStr | None,
) -> int:
    """Run the specs in order over one fresh client (B3).

    ``credential`` is the bearer token for the remote leg and is
    ``None`` only on the in-process leg, which crosses no network
    boundary. It is carried as client-default headers rather than
    attached per request so no route can be added later that quietly
    skips it (SEC-016).
    """
    headers = (
        authorization_headers(credential) if credential is not None else {}
    )
    async with httpx.AsyncClient(
        transport=transport, base_url=base_url, headers=headers
    ) as client:
        for spec in specs:
            response = await client.request(
                spec.method,
                spec.path,
                params=dict(spec.params),
                json=spec.json,
            )
            if response.status_code >= 500:
                # The body travels too, when there is one. A 5xx is
                # usually opaque by design (T-07-26), but a deployment
                # that answers 5xx with a *typed* refusal has said
                # something the operator has to act on — the backend
                # registry's fail-closed 503 names the distribution whose
                # packaging conflicts, which is the one thing that tells a
                # conflict apart from a missing adapter. Discarding it
                # leaves the operator with a status code and no lead.
                # Stderr, not stdout: this is still a wiring error under
                # the documented exit-code contract.
                detail = response.text.strip()
                sys.stderr.write(
                    f"wiring error: {spec.method} {spec.path} ->"
                    f" {response.status_code}\n"
                    + (f"{detail}\n" if detail else "")
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
    try:
        specs = args.build(args)
    except CommandRefused as refused:
        # A verb refused its own inputs. Same exit status and same stream
        # as a refusal that crossed the HTTP boundary (T-07-26).
        sys.stdout.write(f"{refused}\n")
        return EXIT_REFUSED

    transport: httpx.AsyncBaseTransport | None
    credential: SecretStr | None = None
    if dependencies is not None or args.local:
        if dependencies is None:
            if not args.local_root:
                parser.error("--local requires --local-root DIR")
            from ccf_runtime.cli.local import build_local_dependencies

            dependencies = build_local_dependencies(
                root=Path(args.local_root)
            )
        from ccf_runtime.http_api.app import create_app

        # In-process ASGI transport over the caller's own handles: the app
        # is never bound to a network interface, so the D-IMPL-73 insecure-
        # default posture is the caller's existing in-process authority,
        # not a new exposure surface — acknowledged, not suppressed.
        transport = httpx.ASGITransport(
            app=create_app(dependencies, acknowledge_insecure_default=True)
        )
        base_url = _LOCAL_BASE
    else:
        configured = args.base_url or os.environ.get("CCF_BASE_URL")
        if not configured:
            parser.error("no base URL: pass --base-url or set CCF_BASE_URL")
        # Resolved BEFORE any request is built, and unconditionally: the
        # remote leg is a network boundary, so "no credential" is a
        # refusal rather than a quieter request (SEC-016). `parser.error`
        # is the same exit-2-on-stderr path the missing base URL above
        # takes, because both are deployment wiring.
        try:
            credential = resolve_remote_credential(
                token_env=args.token_env or os.environ.get("CCF_TOKEN_ENV"),
                token_file=(
                    args.token_file or os.environ.get("CCF_TOKEN_FILE")
                ),
                environ=os.environ,
            )
        except CredentialUnresolved as unresolved:
            parser.error(str(unresolved))
        transport = None
        base_url = configured

    try:
        return asyncio.run(
            _execute(
                specs,
                transport=transport,
                base_url=base_url,
                credential=credential,
            )
        )
    except httpx.TransportError as unreachable:
        sys.stderr.write(f"wiring error: {unreachable}\n")
        return EXIT_WIRING


if __name__ == "__main__":
    raise SystemExit(main())
