"""Recording forward-proxy for one-time fixture capture (13.2 D-01a/D-02).

An ephemeral tool — not wired into the Makefile or CI. It reuses the same
base-URL seam the replay server does (``ANTHROPIC_BASE_URL`` /
``GOOGLE_GEMINI_BASE_URL``, D-09): point the client legs here instead of
at ``../replay_server.py`` and each request is forwarded to the real
vendor API while its body is teed to disk in the committed fixture naming
scheme (``<prefix>-NN-request.json`` / ``<prefix>-NN.json``).

Routing is by path suffix, exactly as in ``replay_server.py``:

* suffix ``/v1/messages``      -> forwarded to api.anthropic.com,
                                  recorded as ``anthropic-NN``
* suffix ``:generateContent``  -> forwarded to
                                  generativelanguage.googleapis.com,
                                  recorded as ``gemini-NN``

Every request must present a one-time SECRET as the FIRST path segment
(``/<secret>/v1/messages``); see the security posture below.

Recording spec (D-09/D-10, 13.3):

* **Forward** the request path AND query string verbatim, so a capture is
  faithful to the call the SDK actually made (``?alt=sse`` selects a
  different response shape).
* **Record only a 200 carrying JSON.** Every other upstream answer — a
  429, a 500, an SSE stream, an HTML error page — is returned to the
  caller byte-for-byte and consumes NO fixture ordinal, so a transient
  vendor failure cannot renumber the real turns.
* **A request body that is not a JSON object is refused with 400**
  before anything is forwarded, for the same reason: it can never be
  recorded, so it must never claim an ordinal (and must never spend
  vendor credit on a call whose capture is impossible).

Security posture (T-13.2-06/T-13.3-04): API keys ride in HTTP headers, so
headers are NEVER written to disk in either direction. The outbound key is
injected at forward time from ``ANTHROPIC_API_KEY`` / ``GOOGLE_API_KEY``
in the process environment. Only request and response BODIES are
recorded, plus — when the request carried one — the query string under a
reserved key with every key-shaped parameter value replaced by a
placeholder (case-insensitive substring match, :data:`SECRET_QUERY_MARKERS`),
since Gemini also accepts the key as a query parameter.

**Confused-deputy defence (IN-01).** Injecting the operator's real key on
the forward path makes an unauthenticated loopback listener a deputy for
that key: any local process — including a web page issuing a CORS-simple
POST to ``http://127.0.0.1:<port>/`` — could otherwise spend vendor credit
and write attacker-controlled content into the fixture tree. So the proxy
mints a one-time secret at startup and requires it as the FIRST PATH
SEGMENT of every request; anything else is refused ``403`` before a key is
injected, before anything is forwarded, and before an ordinal is claimed.

The secret rides in the path rather than in a header deliberately: the
capture flow points vendor SDKs at the proxy through their own base-URL
variables (``ANTHROPIC_BASE_URL`` / ``GOOGLE_GEMINI_BASE_URL``), and those
SDKs offer no seam for an extra header — but a base URL with a path prefix
they append their own route to needs no SDK cooperation at all. ``main``
prints the exact base URL to export.

Binds 127.0.0.1 on port 0 and prints ``READY <port>`` once started (the
suite's handshake pattern), preceded by the secret-bearing base URL.
Recordings land in an output directory given as ``argv[1]``. The default
is a private scratch directory created by ``tempfile.mkdtemp`` — mode
``0o700``, unguessable name, never the committed ``fixtures/``.
"""

from __future__ import annotations

import json
import os
import secrets
import socket
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode

import anyio
import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

#: Path suffix -> (fixture filename prefix, upstream base, key env var,
#: key header name). Same routing table shape as replay_server.SUFFIXES.
#:
#: **On CLAUDE.md §6.4 (IN-05).** The No-Hardcoding Rule bars routing
#: tables as code constants because routing is normally a *deployment*
#: value the Control Plane owns. This table is not that. It is a
#: transcription of two vendors' published wire protocols — Anthropic
#: serves ``/v1/messages`` and authenticates with ``x-api-key``; Google
#: serves ``:generateContent`` and authenticates with ``x-goog-api-key``.
#: Those facts are fixed by the vendors, not chosen by any deployment, and
#: this module is a stand-in for the vendors themselves rather than fabric
#: code (it imports no CCF). An artifact seam here would let an operator
#: "configure" where Anthropic's API lives, which is not a real degree of
#: freedom. The rule still binds everything the fabric owns: no prompt, no
#: agent definition, no threshold, no policy value appears in this file.
ROUTES: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "/v1/messages",
        "anthropic",
        "https://api.anthropic.com",
        "ANTHROPIC_API_KEY",
        "x-api-key",
    ),
    (
        ":generateContent",
        "gemini",
        "https://generativelanguage.googleapis.com",
        "GOOGLE_API_KEY",
        "x-goog-api-key",
    ),
)

#: Request headers copied upstream. Auth headers are injected separately
#: from env; everything else (including any inbound Authorization or
#: x-api-key from the client) is dropped and re-derived.
FORWARDED_REQUEST_HEADERS = ("content-type", "anthropic-version", "accept")

#: Substrings that mark a query parameter as key-bearing. Matched
#: case-insensitively against the parameter NAME, and by substring rather
#: than equality (D-10): exact-match on {"key", "api_key"} persisted
#: `?Key=`, `?API_KEY=` and `?access_token=` verbatim into a git-tracked
#: directory. Redaction is the only thing between a live key and a
#: committed file, so it takes the conservative side of the trade — a
#: false positive costs one unreviewable query value, a false negative
#: costs a leaked credential.
SECRET_QUERY_MARKERS = ("key", "token", "secret", "password", "auth")

#: Placeholder written in place of a redacted query value.
REDACTED = "REDACTED"

#: Reserved key under which a non-empty, redacted request query is
#: recorded in the request fixture. Absent when the request had no query,
#: which is why the committed (query-less) 13.2 fixtures are unaffected.
QUERY_KEY = "__request_query__"


def is_secret_query_param(name: str) -> bool:
    """Does this query-parameter name look key-bearing? (D-10)

    Case-folded substring match against :data:`SECRET_QUERY_MARKERS`, so
    ``Key``, ``API_KEY`` and ``access_token`` are all caught alongside the
    literal ``key`` Gemini documents.
    """
    lowered = name.lower()
    return any(marker in lowered for marker in SECRET_QUERY_MARKERS)


def redact_query(query: str) -> str:
    """Replace every key-bearing query value with the placeholder (D-10).

    Gemini accepts ``?key=`` as an alternative to the header, so a
    faithfully-captured query can carry live key material. Parsed and
    re-encoded rather than string-spliced, so an escaped or repeated
    parameter cannot slip a secret past the filter.
    """
    return urlencode(
        [
            (name, REDACTED if is_secret_query_param(name) else value)
            for name, value in parse_qsl(query, keep_blank_values=True)
        ]
    )


def strip_secret(path: str, secret: str) -> str | None:
    """Consume the leading secret path segment, or ``None`` if absent (IN-01).

    ``/<secret>/v1/messages`` -> ``/v1/messages``. Compared in constant
    time, because the whole point of the segment is that a local caller
    cannot guess it. Returns ``None`` on **every** mismatch — including a
    segment this function cannot even compare as text — which the handler
    turns into a ``403`` before a key is injected or an ordinal claimed.

    **Why UTF-8 bytes and not ``str`` (WR-01).** ``compare_digest`` refuses
    ``str`` operands containing non-ASCII characters, raising
    ``TypeError``. Uvicorn and the Starlette ``TestClient`` percent-decode
    ``scope["path"]``, so ``POST /%C3%A9/v1/messages`` presented ``"é"``
    here and crashed the one function whose whole job is to refuse
    unauthenticated requests cleanly — an anonymous ``500`` instead of the
    documented ``403``. Encoding both operands makes every byte string
    comparable while keeping the comparison constant-time; do not add a
    length short-circuit, which would leak the secret's length.
    """
    segments = path.split("/", 2)
    presented = segments[1] if len(segments) > 1 else ""
    if not secrets.compare_digest(
        presented.encode("utf-8"), secret.encode("utf-8")
    ):
        return None
    return "/" + (segments[2] if len(segments) > 2 else "")


def build_app(
    out_dir: Path,
    *,
    secret: str,
    transport: httpx.BaseTransport | None = None,
) -> Starlette:
    """Host the capture proxy, writing fixture pairs into ``out_dir``.

    ``secret`` is the one-time capture secret every request must present as
    its first path segment (IN-01); it is REQUIRED rather than defaulted,
    so there is no construction path that yields an open deputy for the
    operator's API key. ``main`` mints one per process.

    ``transport`` is the injection seam the tests use to stand in a fake
    upstream; production capture leaves it ``None`` and httpx dials the
    real vendor.

    ``out_dir`` is created if absent. For the DEFAULT directory this is a
    no-op — :func:`default_out_dir` has already created it atomically at
    mode ``0o700`` (WR-02). The permissive ``exist_ok`` therefore applies
    only to a directory the operator named explicitly on the command line,
    where reusing or pre-creating the path is their own deliberate choice
    rather than something a third party can predict.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    counters: dict[str, int] = {prefix: 0 for _, prefix, *_ in ROUTES}

    async def capture(request: Request) -> Response:
        # IN-01: the secret is checked FIRST — before the route is matched,
        # before a key leaves the environment, before anything is forwarded,
        # and before an ordinal is claimed. An unauthenticated local caller
        # can neither spend vendor credit nor renumber the fixture sequence.
        path_or_none = strip_secret(request.url.path, secret)
        if path_or_none is None:
            return JSONResponse(
                {
                    "error": "missing or incorrect capture secret; it is the "
                    "first path segment, and main() prints the base URL "
                    "to export"
                },
                status_code=403,
            )
        path = path_or_none
        for suffix, prefix, base, key_env, key_header in ROUTES:
            if not path.endswith(suffix):
                continue
            key = os.environ.get(key_env)
            if not key:
                return JSONResponse(
                    {"error": f"{key_env} not set in proxy environment"},
                    status_code=500,
                )
            body = await request.body()
            # D-09 ordinal conservation: a request whose body cannot be
            # recorded is not a capturable turn, so it is refused BEFORE
            # anything is forwarded and BEFORE an ordinal is claimed. Doing
            # the parse after the ordinal claim spent an ordinal on an
            # unhandled 500 — the exact renumbering hazard D-09 exists to
            # prevent.
            try:
                parsed = json.loads(body)
            except ValueError:
                parsed = None
            if not isinstance(parsed, dict):
                return JSONResponse(
                    {
                        "error": "request body is not a JSON object; "
                        "nothing forwarded, no ordinal consumed",
                        "path": path,
                    },
                    status_code=400,
                )
            request_doc: dict[str, object] = parsed
            headers = {key_header: key}
            for name in FORWARDED_REQUEST_HEADERS:
                if name in request.headers:
                    headers[name] = request.headers[name]
            # D-10: path AND query, verbatim. Dropping the query made the
            # capture unfaithful to the call the SDK actually made
            # (``?alt=sse`` selects a different response shape entirely).
            query = request.url.query
            target = f"{base}{path}" + (f"?{query}" if query else "")
            async with httpx.AsyncClient(
                timeout=120.0, transport=transport
            ) as client:
                upstream = await client.post(
                    target, content=body, headers=headers
                )
            # D-09: only a 200 carrying JSON is a recordable turn. Anything
            # else — a 429, a 500, an SSE stream, an HTML error page — goes
            # back to the caller byte-for-byte and consumes NO ordinal, so a
            # transient failure cannot shift the real turns' numbering.
            try:
                response_doc = (
                    upstream.json() if upstream.status_code == 200 else None
                )
            except ValueError:
                response_doc = None
            if response_doc is None:
                return Response(
                    content=upstream.content,
                    status_code=upstream.status_code,
                    media_type=upstream.headers.get("content-type"),
                )
            ordinal = counters[prefix]
            counters[prefix] = ordinal + 1
            # BODIES ONLY, both directions — headers carry key material and
            # are never serialized, in either direction (T-13.2-06). The one
            # non-body datum recorded is the request query, and only when
            # present, under a reserved key, with key-bearing params redacted
            # (D-10/T-13.3-04) — so a captured `?alt=` stays reviewable while
            # a captured `?key=` cannot reach the fixture tree. The body was
            # parsed and shape-checked before the ordinal was claimed.
            if query:
                request_doc[QUERY_KEY] = redact_query(query)
            (out_dir / f"{prefix}-{ordinal:02d}-request.json").write_text(
                json.dumps(request_doc, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            (out_dir / f"{prefix}-{ordinal:02d}.json").write_text(
                json.dumps(response_doc, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            return JSONResponse(
                response_doc, status_code=upstream.status_code
            )
        return JSONResponse(
            {"error": "no capture route for path", "path": path},
            status_code=500,
        )

    return Starlette(
        routes=[Route("/{rest:path}", capture, methods=["POST"])]
    )


def default_out_dir(now: datetime | None = None) -> Path:
    """Create and return a private scratch directory under the temp dir.

    IN-02: the default used to be this committed ``fixtures/`` directory,
    so a capture run with no ``argv[1]`` overwrote ``anthropic-00.json``
    and friends in place. Git makes that recoverable, which is not the same
    as making it acceptable — a one-time capture tool should not have a
    destructive default. Promotion into ``fixtures/`` is an explicit
    reviewed ``mv`` (README.md), exactly as D-10 intends.

    **Created here, not merely named (WR-01/WR-02).** The first cut of this
    fix returned ``<tempdir>/ccf-ext00-capture-<stamp>`` at second
    granularity and let the caller ``mkdir(exist_ok=True)`` it. That name
    is fully derivable by any other local process, and the system temp dir
    is shared: a hostile same-host process could pre-create the path — as a
    directory it owns, or as a symlink pointing elsewhere — and
    ``exist_ok=True`` would have accepted it silently, putting the captured
    vendor request and response bodies (which the operator then promotes
    into the git tree) somewhere it controls. That is the same threat model
    the IN-01 capture secret defends against, so leaving it half-open was
    inconsistent. Two same-second runs also collided onto one directory and
    overwrote each other's ordinal ``00``.

    ``tempfile.mkdtemp`` closes both: it creates the directory atomically,
    mode ``0o700``, with a random suffix that cannot be guessed or
    collided with. The timestamp is retained only as a human-readable
    prefix so an operator can tell two capture runs apart at a glance; it
    is decoration, not the uniqueness mechanism.
    """
    stamp = (now or datetime.now()).strftime("%Y%m%dT%H%M%S")
    return Path(tempfile.mkdtemp(prefix=f"ccf-ext00-capture-{stamp}-"))


def main() -> None:
    """Bind loopback port 0, host the capture app, announce READY."""
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else default_out_dir()
    # IN-01: minted per process, never persisted, never logged to a file.
    secret = secrets.token_urlsafe(24)

    bound = socket.socket()
    bound.bind(("127.0.0.1", 0))
    bound.listen(64)
    port = bound.getsockname()[1]

    server = uvicorn.Server(
        uvicorn.Config(build_app(out_dir, secret=secret), log_level="error")
    )

    async def host() -> None:
        async def announce() -> None:
            while not server.started:
                await anyio.sleep(0.005)
            print(f"recording into {out_dir}", flush=True)
            print(
                "export this as ANTHROPIC_BASE_URL / "
                f"GOOGLE_GEMINI_BASE_URL: http://127.0.0.1:{port}/{secret}",
                flush=True,
            )
            print(f"READY {port}", flush=True)

        async def serve() -> None:
            await server.serve(sockets=[bound])

        async with anyio.create_task_group() as group:
            group.start_soon(announce)
            group.start_soon(serve)

    anyio.run(host)


if __name__ == "__main__":
    main()
