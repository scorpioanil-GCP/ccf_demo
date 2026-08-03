"""examples/external/00-hello-context — transport-level model-API replay (D-09).

CI determinism for the LLM client legs without a single code branch in
them: the legs' SDKs are pointed here via their own base-URL environment
variables (``ANTHROPIC_BASE_URL``, ``GOOGLE_GEMINI_BASE_URL``), and this
server answers each POST with a recorded fixture, verbatim. Live mode is
the same client code with the env vars unset — this server is then simply
not in the path.

Routing is by PATH SUFFIX, not exact path, because each SDK appends its
own route to the base URL:

* suffix ``/v1/messages``      -> Anthropic Messages-API fixtures
* suffix ``:generateContent``  -> Gemini generateContent fixtures

Fixtures are matched ordinal-per-path: the first matching request gets
fixture index 0, the next gets 1, and so on — adequate for a fixed, short
tool-use conversation, and simple enough to review. Fixture files live in
``fixtures/`` (``anthropic-00.json``, ``gemini-00.json``, …), each with a
sibling ``*-request.json`` recorded-request file. Before serving ordinal
N, a per-path fingerprint of the incoming body is compared against the
recorded request N (D-03): a drifted request is answered 500 with a JSON
diagnostic naming the path, the ordinal, and the ``expected`` vs
``actual`` fingerprints — fail loudly, never serve the wrong fixture. A
request past the last fixture for its path is likewise answered 500
naming the exhausted path — fail loudly, never loop.

Pairing is checked BEFORE ``READY``: any fixture missing its sibling, in
either direction, refuses startup with the unpaired filenames on stderr
(D-06). There is therefore no ordinal that serves without a fingerprint
comparison. For Gemini the comparison includes the model segment of the
URL path, since that API carries the model in the URL rather than the
body (D-08) — which catches a client leg that does not honour the pinned
model label. It does NOT verify that the recorded fixture was captured
against that model: both sides of that field come from the harness, not
from the fixture. See :func:`fingerprint` for the exact guarantee.

No CCF imports: this is a stand-in for a vendor's model API, and the
fabric is not involved. Binds 127.0.0.1 on port 0 and prints
``READY <port>`` once started (the suite's handshake pattern), including
when ``fixtures/`` is empty or absent — plan 03 authors the fixtures.
"""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

import anyio
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

_EXAMPLE_ROOT = Path(__file__).resolve().parent
FIXTURES = _EXAMPLE_ROOT / "fixtures"

#: Path suffix -> fixture filename prefix. The whole routing table.
#:
#: **On CLAUDE.md §6.4 (IN-05).** The No-Hardcoding Rule names routing
#: tables explicitly, so recording the judgment rather than leaving it
#: implicit: this table is a vendor wire-protocol fact, not Control Plane
#: configuration. Anthropic's Messages API is reached at ``/v1/messages``
#: and Google's Generate-Content API at ``:generateContent`` — the vendors
#: fix those paths; no deployment chooses them, and no operator has a
#: reason to reconfigure them. This module is a stand-in for the vendors
#: themselves (it imports nothing from CCF), so an artifact seam here would
#: manufacture a degree of freedom that does not exist. The rule binds in
#: full everywhere it has purchase: no prompt, no agent or task definition,
#: no threshold, no policy value is expressed as a constant in this file,
#: and the fixture LABELS this server compares against arrive from
#: ``run.py`` and the fixtures, never from a literal here.
SUFFIXES: tuple[tuple[str, str], ...] = (
    ("/v1/messages", "anthropic"),
    (":generateContent", "gemini"),
)


def find_orphans(fixtures_dir: Path) -> list[str]:
    """Return every fixture filename missing its sibling, both directions.

    A response fixture without its ``*-request.json`` sibling would be
    served unfingerprinted; a recorded request without its response is a
    half-captured conversation. Both are broken pairs, so both are
    reported (D-06). A missing or empty directory yields no orphans —
    zero fixtures is a valid state.

    The ``{prefix}-*.json`` glob is the discipline that keeps sibling
    tooling in this directory (``capture_proxy.py``, ``README.md``,
    ``diff_fixtures.py``) out of the scan.
    """
    if not fixtures_dir.is_dir():
        return []
    orphans: list[str] = []
    for _, prefix in SUFFIXES:
        responses: set[str] = set()
        requests: set[str] = set()
        for path in sorted(fixtures_dir.glob(f"{prefix}-*.json")):
            name = path.name
            if name.endswith("-request.json"):
                requests.add(name[: -len("-request.json")])
            else:
                responses.add(name[: -len(".json")])
        orphans.extend(f"{stem}.json" for stem in sorted(responses - requests))
        orphans.extend(
            f"{stem}-request.json" for stem in sorted(requests - responses)
        )
    return orphans


def require_paired_fixtures(fixtures_dir: Path) -> None:
    """Refuse to start when any fixture is unpaired (D-06).

    Called before ``READY`` is announced, so ``run.py``'s blocking
    readline sees the child die rather than a server that would skip
    fingerprinting for the orphaned ordinal.
    """
    orphans = find_orphans(fixtures_dir)
    if orphans:
        print(
            "unpaired fixtures in "
            f"{fixtures_dir} — every '{{prefix}}-NN.json' needs its "
            "'{prefix}-NN-request.json' sibling and vice versa: "
            + ", ".join(orphans),
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)


def _load_fixtures(fixtures_dir: Path) -> dict[str, list[dict[str, object]]]:
    """Load every fixture pair at startup, ordered by filename ordinal.

    Callers run ``require_paired_fixtures`` first, so every response here
    has its recorded request and the handler can fingerprint
    unconditionally. A missing or empty directory is a valid state (zero
    fixtures loaded); startup still succeeds.
    """
    loaded: dict[str, list[dict[str, object]]] = {
        prefix: [] for _, prefix in SUFFIXES
    }
    if not fixtures_dir.is_dir():
        return loaded
    for _, prefix in SUFFIXES:
        for path in sorted(fixtures_dir.glob(f"{prefix}-*.json")):
            if path.name.endswith("-request.json"):
                continue
            request_path = path.with_name(
                path.name.replace(".json", "-request.json")
            )
            loaded[prefix].append(
                {
                    "response": json.loads(
                        path.read_text(encoding="utf-8")
                    ),
                    "request": json.loads(
                        request_path.read_text(encoding="utf-8")
                    ),
                }
            )
    return loaded


def url_model(path: str) -> str:
    """Extract the model segment from a Gemini generateContent URL path.

    ``/v1beta/models/<model>:generateContent`` -> ``<model>``. Returns ""
    when the path carries no such segment.
    """
    if ":" not in path:
        return ""
    return path.rsplit("/", 1)[-1].split(":", 1)[0]


def fingerprint(
    prefix: str,
    body: dict[str, object],
    path: str = "",
    *,
    expected_gemini_model: str = "",
) -> dict[str, object]:
    """Reduce a request to the drift-detecting shape for its path.

    A pure reduction: everything it depends on arrives as an argument.
    (It formerly read ``CCF_EXT00_GEMINI_MODEL`` from the process
    environment, which made an otherwise pure function depend on ambient
    state and made an unset variable indistinguishable from an
    intentionally empty model.) :func:`build_app` resolves the pinned
    label once and passes it in.

    Anthropic (``/v1/messages``): model, sorted tool names, message
    count. Gemini (``:generateContent``): sorted function-declaration
    names, content count, and the model segment of the URL — the Gemini
    body carries NO model field, so without the URL the model is not in
    the comparison at all (D-08).

    ``path`` is the ACTUAL side of the comparison — the URL the client leg
    really emitted. The committed request fixtures are body-only (D-11, no
    re-capture), so the EXPECTED side passes no path and takes
    ``expected_gemini_model``, the label ``run.py`` pins.

    **What the Gemini model comparison does and does not guarantee.** Both
    sides of ``url_model`` derive from the harness, not from the recorded
    fixture: the expected side is the pinned label, the actual side is the
    URL ``client_adk.py`` emits. So it catches a client leg that ignores
    the pinned model — a real seam — but it CANNOT detect that a fixture
    was recorded against a different model than the one now pinned.
    Fixture-vs-model correspondence is unverified and stays unverified
    until a re-capture records the model into the request fixture (D-11
    forbids re-capture this phase).

    Intentional residual (D-08): the field set stays coarse — a request
    with the same model, tools, and counts but different message content
    still matches. Documented, not fixed.
    """
    if prefix == "anthropic":
        tools = body.get("tools") or []
        return {
            "model": body.get("model"),
            "tool_names": sorted(
                t.get("name") for t in tools if isinstance(t, dict)
            ),
            "message_count": len(body.get("messages") or []),
        }
    declarations = []
    tools = body.get("tools") or []
    if tools and isinstance(tools[0], dict):
        declarations = tools[0].get("functionDeclarations") or []
    return {
        "function_names": sorted(
            d.get("name") for d in declarations if isinstance(d, dict)
        ),
        "content_count": len(body.get("contents") or []),
        "url_model": url_model(path) if path else expected_gemini_model,
    }


#: Env seam through which ``run.py`` pins the Gemini fixture label.
GEMINI_MODEL_ENV = "CCF_EXT00_GEMINI_MODEL"


def build_app(
    fixtures_dir: Path = FIXTURES, *, expected_gemini_model: str | None = None
) -> Starlette:
    """Host the replay app over ``fixtures_dir``.

    ``expected_gemini_model`` is the EXPECTED side of the Gemini
    ``url_model`` comparison (see :func:`fingerprint`). It is resolved
    ONCE, here, from the argument or the :data:`GEMINI_MODEL_ENV` seam
    ``run.py`` sets — never read inside the reduction. When it resolves to
    ``None`` and a Gemini request arrives, the handler answers a loud 500
    naming the unset variable rather than fingerprinting an empty model
    against a real one and reporting a mismatch no operator can interpret.
    Anthropic replay is unaffected, so standalone ``python
    replay_server.py`` still starts and still serves that leg.

    **Empty is unset (NEW-01).** ``CCF_EXT00_GEMINI_MODEL=`` — an exported
    but empty variable, which is what a shell yields from an unset
    substitution such as ``CCF_EXT00_GEMINI_MODEL="$SOME_TYPO"`` — used to
    count as SET: it skipped the loud-500 path and fingerprinted
    ``url_model: ""`` against a real model, producing exactly the
    uninterpretable mismatch the 500 exists to prevent. There is no such
    thing as an intentionally empty model label, so empty collapses to
    ``None`` here and takes the named refusal.
    """
    fixtures = _load_fixtures(fixtures_dir)
    cursors: dict[str, int] = {prefix: 0 for _, prefix in SUFFIXES}
    resolved = (
        expected_gemini_model
        if expected_gemini_model is not None
        else os.environ.get(GEMINI_MODEL_ENV)
    )
    pinned_gemini_model = resolved or None

    async def replay(request: Request) -> Response:
        path = request.url.path
        for suffix, prefix in SUFFIXES:
            if not path.endswith(suffix):
                continue
            ordinal = cursors[prefix]
            recorded = fixtures[prefix]
            if ordinal >= len(recorded):
                # Fail loudly, never loop: a fixture shortfall means the
                # conversation drifted from the recorded one, and the review
                # event is regeneration (D-10), not silent reuse.
                return JSONResponse(
                    {
                        "error": "fixtures exhausted",
                        "path": path,
                        "served": ordinal,
                    },
                    status_code=500,
                )
            try:
                body = await request.json()
            except Exception:
                # T-13.2-09: a malformed body gets the same loud 500
                # diagnostic shape, never an unhandled exception.
                return JSONResponse(
                    {
                        "error": "request body is not valid JSON",
                        "path": path,
                        "ordinal": ordinal,
                    },
                    status_code=500,
                )
            # Every ordinal has a recorded request: startup refused
            # otherwise (D-06), so there is no unfingerprinted serve path.
            if prefix == "gemini" and pinned_gemini_model is None:
                # Loud and named, never a silent "" that produces an
                # uninterpretable mismatch diagnostic.
                return JSONResponse(
                    {
                        "error": (
                            f"{GEMINI_MODEL_ENV} is not set; it pins the "
                            "expected side of the Gemini model comparison "
                            "and run.py supplies it"
                        ),
                        "path": path,
                        "ordinal": ordinal,
                    },
                    status_code=500,
                )
            recorded_request = recorded[ordinal]["request"]
            expected = fingerprint(
                prefix,
                recorded_request,
                expected_gemini_model=pinned_gemini_model or "",
            )
            actual = fingerprint(prefix, body, path)
            if expected != actual:
                # D-03: drift fails loudly with a diagnostic naming
                # both fingerprints — never serve the wrong fixture.
                return JSONResponse(
                    {
                        "error": "request fingerprint mismatch",
                        "path": path,
                        "ordinal": ordinal,
                        "expected": expected,
                        "actual": actual,
                    },
                    status_code=500,
                )
            cursors[prefix] = ordinal + 1
            return JSONResponse(recorded[ordinal]["response"])
        return JSONResponse(
            {"error": "no fixture route for path", "path": path},
            status_code=500,
        )

    return Starlette(
        routes=[
            Route("/{rest:path}", replay, methods=["POST"]),
        ]
    )


def main() -> None:
    """Bind loopback port 0, host the replay app, announce READY."""
    # Before anything else, and before READY: an unpaired fixture is a
    # startup refusal, never a quietly unguarded ordinal (D-06).
    require_paired_fixtures(FIXTURES)

    bound = socket.socket()
    bound.bind(("127.0.0.1", 0))
    bound.listen(64)
    port = bound.getsockname()[1]

    server = uvicorn.Server(
        uvicorn.Config(build_app(FIXTURES), log_level="error")
    )

    async def host() -> None:
        async def announce() -> None:
            while not server.started:
                await anyio.sleep(0.005)
            print(f"READY {port}", flush=True)

        async def serve() -> None:
            await server.serve(sockets=[bound])

        async with anyio.create_task_group() as group:
            group.start_soon(announce)
            group.start_soon(serve)

    anyio.run(host)


if __name__ == "__main__":
    main()
