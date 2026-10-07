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
from typing import TYPE_CHECKING
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

if TYPE_CHECKING:
    from ccf_runtime.http_api.app import HttpAuthority

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
    parser.add_argument(
        "--local-hitl-policy-key",
        help=(
            "the deployment's HITL policy key the --local transport and erasure"
            " consult are bound to (SEC-009)"
        ),
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
    authority: HttpAuthority | None = None,
    credential: SecretStr | None = None,
) -> int:
    """Parse, translate, and execute one CLI invocation.

    Args:
        argv: Argument vector; ``None`` reads ``sys.argv``.
        dependencies: Optional injected bundle (tests; embedding). When
            supplied, the command runs in-process over these handles —
            the same type ``create_app`` consumes.
        authority: The five seams ``create_app`` requires, as one
            :class:`~ccf_runtime.http_api.app.HttpAuthority` bundle, for
            the in-process path — typed, so an incomplete bundle is a
            type error where it is written. **Required whenever
            ``dependencies`` is supplied**: the gate has no arm in which
            authentication is skipped (``SEC-002``), so an in-process app
            is built with a real authority or not at all. There is no
            value of this parameter that produces an unauthenticated
            application — omitting it refuses rather than defaulting.
        credential: The bearer the in-process leg presents. Required
            alongside ``authority`` for the same reason the remote leg
            requires one: the gate is TOTAL, so an in-process request is a
            request like any other and the absence of a network boundary
            entitles it to nothing (``SEC-002``, ``SEC-016``).
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
    # `credential` is the parameter: the in-process leg is handed one
    # by its embedder, the remote leg resolves its own below. A local
    # re-declaration here would shadow the parameter and silently send
    # the in-process request anonymously (found at the Tier-1 join).
    if dependencies is not None or args.local:
        if dependencies is None:
            if not args.local_root:
                parser.error("--local requires --local-root DIR")
            if not args.local_hitl_policy_key:
                parser.error("--local requires --local-hitl-policy-key KEY")
            from ccf_runtime.cli.local import build_local_dependencies

            dependencies = build_local_dependencies(
                root=Path(args.local_root),
                hitl_policy_key=args.local_hitl_policy_key,
            )
        if dependencies is not None and authority is not None:
            # The in-process path with a REAL authority: an embedder or a
            # test supplies the same five seams a deployment does, so the
            # app the CLI drives is the app everyone else gets.
            from ccf_runtime.http_api.app import create_app

            transport = httpx.ASGITransport(
                app=create_app(dependencies, **authority)
            )
            base_url = _LOCAL_BASE
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

        # `--local` is SUSPENDED, and it fails closed rather than quietly
        # building a weaker app (`SEC-002`; `D-IMPL-352` conservative
        # posture).
        #
        # It used to pass `acknowledge_insecure_default=True`, which was the
        # in-process reading of `D-IMPL-73`. That ruling is deleted: the gate
        # now has no arm in which authentication is skipped, and the SDK
        # ships exactly one authorizer — `ControlPlaneTenantAuthorizer` —
        # which is deny-by-default against a scope mapping registered at a
        # pinned version. `build_local_dependencies` mints a FRESH, EMPTY
        # `ControlPlaneRegistry` per invocation, so there is nothing for that
        # authorizer to decide against, and `create_app`'s other three seams
        # are required now too.
        #
        # Reviving the mode means declaring a real local deployment — a
        # scope mapping, a token source, an entitlement source, a perspective
        # resolver and a refusal recorder. That is a decision about what
        # `--local` MEANS, not a wiring detail, so it is Dave's and is not
        # taken here. Refusing is the honest interim: the remote leg is
        # unaffected and fully functional.
        if not args.local:
            # An embedder supplied handles but no authority. Refusing is
            # right; telling them about `--local` would not be, since they
            # never asked for it. Keyed on `args.local` and NOT on
            # `dependencies`, which `build_local_dependencies` has already
            # populated by this point — that is how this diagnostic first
            # answered the wrong caller.
            parser.error(
                "in-process invocation needs `authority=`: `create_app`"
                " requires an auth hook, an authorizer, an entitlement"
                " source, a perspective resolver and a refusal recorder,"
                " and none of them has a default (`SEC-002`)."
            )
        parser.error(
            "`--local` is suspended: it built an app with"
            " `acknowledge_insecure_default`, and that posture is deleted."
            " The mode returns once a local deployment declares a scope"
            " mapping, a token source, an entitlement source, a perspective"
            " resolver and a refusal recorder. Use `--base-url` against a"
            " running deployment meanwhile (`SEC-002`)."
        )
        raise AssertionError("unreachable: parser.error exits")  # pragma: no cover
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
