"""examples/external/00-hello-context — one command, four legs, eight assertions.

The fabric-side orchestrator (CCF imports are allowed HERE and only here —
the client legs stay zero-CCF-import by charter, D-05/D-06). One process
spawns the black-box front door (``serve.py``), the transport-level
model-API replay server (``replay_server.py``, D-09), runs the three
runnable client legs against them, and then asserts — fabric-side — that
everything the family charter claims actually held:

1. **Legs exit 0.** ``client_bare.py``, ``client_anthropic.py``, and
   ``client_adk.py`` each consume the authenticated MCP front door
   (CLAUDE.md §8.3; whitepaper §8.3 Pattern 3) end to end, offline.
2. **Auth refusal (D-12).** The REVOKED token from ``artifacts/tokens.yaml``
   is rejected with HTTP 401 — bearer auth is on from day one and a passing
   CI run proves the refusal path stays live (T-13.1-11).
3. **Zero CCF imports in the client legs (D-06).** A static grep over
   ``client_*.py`` — the charter's mechanical enforcement.
4. **Seven-heading README (D-17/D-08).** The seven Phase-13 D-02 template
   headings, matched by exact name and order (``README_HEADINGS``); the
   ``.mcp.json`` docs-only leg lives there.
5. **D-15 retrieval.** The bare leg's output shows lineage AND the
   five-dimension Decision Replay record (whitepaper §7.10) retrieved over
   the same authenticated MCP surface the product came from.
6. **D-07 byte-path probe.** In one authenticated session, the templated
   Experience resource and the ``get_context`` tool serve byte-identical
   product serializations — the dual serve paths cannot silently diverge.
7. **Allowlist visibility (D-05).** ``tools/list`` advertises exactly the
   tool names ``artifacts/experience.yaml`` allowlists — nothing more.
8. **D-16 byte-equal reproduction (T-13.1-12).** The serve-time replay
   record is resolved from the file-backed ArtifactStore (CLAUDE.md §7.4)
   at its exact content address, replayed through
   ``ccf.replay.engine.replay`` against a rebuilt-from-artifacts fabric,
   and the reproduced product's canonical bytes equal the bytes the front
   door actually served.

Every domain and deployment value comes from ``artifacts/*.yaml`` or the
versioned ``fixtures/`` (CLAUDE.md §6.4); this file interprets. Readiness
is a ``readline()`` on each child's ``READY <port>`` line, bounded by
``READY_TIMEOUT_SECONDS`` — no sleeps, and no unbounded wait either.
Children are terminated in ``finally`` with a kill fallback (T-13.1-14;
example-04 precedent).

Run it: ``make example-ext-00``. Live variants (never CI, D-11):
``make example-ext-00-live-anthropic`` / ``make example-ext-00-live-adk``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import select
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

_EXAMPLE_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _EXAMPLE_ROOT.parents[2]

# Spawned as a bare `python <file>`; resolve roots from __file__ so the
# example runs from anywhere. The example dir itself goes on the path so
# the sibling fabric module (`serve.py`) imports as deployment code.
for _root in (
    str(_EXAMPLE_ROOT),
    str(_REPO_ROOT / "src"),
    str(_REPO_ROOT / "runtime"),
):
    if _root not in sys.path:
        sys.path.insert(0, _root)

import httpx  # noqa: E402
import yaml  # noqa: E402
from pydantic import AnyUrl  # noqa: E402
from mcp import ClientSession  # noqa: E402
from mcp.client.streamable_http import streamablehttp_client  # noqa: E402

import serve as fabric  # noqa: E402  — the sibling fabric-side module

from ccf.artifacts.file_store import FileArtifactStore  # noqa: E402
from ccf.contracts.canonical import canonical_bytes  # noqa: E402
from ccf.controlplane.artifacts import (  # noqa: E402
    DeclaredArtifact,
    OperatorParametersArtifact,
    ProductClassDeclaration,
    ProjectionRequirements,
    SignalBatch,
)
from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: E402
from ccf.deployment import (  # noqa: E402
    BootedFabric,
    build_operator_registry,
    load_and_boot,
    refuse_operator_set_divergence,
)
from ccf.products.contract import (  # noqa: E402
    ContextProductContract,
    ProductLineage,
)
from ccf.projection.engine import OperatorRegistry  # noqa: E402
from ccf.replay.engine import replay, resolve_artifact  # noqa: E402
from ccf.replay.record import DecisionReplayRecord  # noqa: E402

from datetime import datetime, timedelta  # noqa: E402

ARTIFACTS = _EXAMPLE_ROOT / "artifacts"
FIXTURES = _EXAMPLE_ROOT / "fixtures"
TERMINATE_TIMEOUT_SECONDS = 10.0
#: Bound on the wait for a child's `READY <port>` line. Generous enough
#: for a cold uvicorn start on a loaded CI runner, finite so a child that
#: starts but never binds fails the build with a diagnostic instead of
#: hanging it (no diagnostic, no timeout, no signal).
READY_TIMEOUT_SECONDS = 60.0
ALL_LEGS = ("bare", "anthropic", "adk")

#: Fixture-matching label for the Gemini leg. The Anthropic label is read
#: from the recorded request body itself; the Gemini Generate-Content API
#: carries the model in the URL path, which the recorded request bodies do
#: not include, so the label the CI harness passes is stated here exactly
#: as ``fixtures/README.md`` documents it. It names a fixture, never a
#: deployment model — live model names live in ``artifacts/experience.yaml``.
GEMINI_FIXTURE_LABEL = "gemini-fixture"

#: The seven Phase-13 D-02 template headings, by exact name and in order
#: (D-08). One module-level tuple is the single source of truth for the
#: README structural assertion — a count alone would accept a renamed or
#: reordered README (RESEARCH Pitfall 6).
README_HEADINGS = (
    "What this demonstrates",
    "Run it",
    "The story",
    "Artifact-by-artifact",
    "Whitepaper / CLAUDE.md sections exercised",
    "What to change first",
    "What would fail",
)


class HelloReplayEnvironment:
    """The deployment side of the replay seam (``ReplayEnvironment``).

    The projection, operators, and product envelope are rebuilt from the
    SAME artifacts ``serve.py`` assembled from — the ones
    ``artifacts/manifest.yaml`` enumerates, parsed once by ``load_and_boot``
    and handed back on ``BootedFabric.artifacts`` — and the engine VERIFIES
    every one of them against the record rather than trusting this class
    (example-06 pattern; whitepaper §7.10; D-IMPL-26/44).
    """

    def __init__(self, *, booted: BootedFabric) -> None:
        self._booted = booted
        self._governance = cast(
            DeclaredArtifact, booted.artifacts["product-governance"]
        ).declaration
        self._decision = cast(
            DeclaredArtifact, booted.artifacts["decision"]
        ).declaration
        self._declared = cast(
            ProductClassDeclaration, booted.artifacts["product-class"]
        )
        self._requirements = cast(
            ProjectionRequirements, booted.artifacts["projection-requirements"]
        )

    def resolve_plan(self, *, plan_id: str) -> Any:
        if plan_id != self._governance["plan_id"]:
            raise LookupError(plan_id)
        # `required` comes from the PROJECTION's own artifact, never from the
        # rebuilt registry's own keys and never from the product class, which
        # under design E2 is the CLAIM rather than the plan's input. The binder
        # runs here too: a reproduction that planned from a requirements
        # document the product class contradicts would rebuild a product the
        # original deployment's governance disowns, and this is the last point
        # before the engine at which that is still catchable.
        plan = fabric.CreditContextPlan(
            plan_id=plan_id, required=self._requirements.required_operator_keys
        )
        refuse_operator_set_divergence(declared=self._declared, plan=plan)
        return plan

    def resolve_operators(
        self, *, operator_keys: tuple[str, ...]
    ) -> OperatorRegistry:
        boundary = datetime.fromisoformat(self._decision["temporal_boundary"])
        view = self._booted.handle.reader.as_of(
            tenant_id=self._booted.tenant_id, at=boundary
        )
        parameters: Mapping[str, OperatorParametersArtifact] = {
            key: cast(OperatorParametersArtifact, self._booted.artifacts[key])
            for key in fabric.OPERATOR_PARAMETER_KEYS
        }
        return build_operator_registry(
            parameters=parameters,
            view=view,
            pins=self._booted.pins,
            policy_bundle_key=fabric.POLICY_BUNDLE_KEY,
            similarity_index_version=self._governance[
                "similarity_index_version"
            ],
        )

    def rehydrate_product(
        self, *, record: DecisionReplayRecord, projection: Any
    ) -> ContextProductContract:
        now = datetime.fromisoformat(self._decision["now"])
        return ContextProductContract(
            schema_name=self._declared.schema_name,
            schema_version=self._declared.schema_version,
            plan_id=projection.plan_id,
            tenant_id=record.tenant_id,
            temporal_boundary=record.context_fabric_snapshot.temporal_boundary,
            expires_at=now
            + timedelta(seconds=self._governance["product_ttl_seconds"]),
            ttl_anchor=self._declared.ttl_anchor,
            lineage=ProductLineage(
                operators_invoked=frozenset(
                    record.content_generation_path.operator_plan
                ),
                policy_bundle_versions=frozenset(
                    binding.version
                    for binding in record.policy_bindings.bindings
                ),
                graph_snapshot_at=record.context_fabric_snapshot.temporal_boundary,
            ),
            # Read back off dimension 5, never re-assessed: `debt` is inside
            # the product's content address (D-IMPL-100).
            payload=projection.payload,
            debt=record.content_generation_path.debt,
            # And what that debt pointed at, for a harder reason (D-IMPL-118):
            # the carrier is a top-level vessel field, so `(record, projection)`
            # names it nowhere else and omitting it diverges every replay.
            debt_evidence=record.content_generation_path.debt_evidence,
            # And when its sources last published, for the same reason again
            # (D-IMPL-117 gap 2): the second Track B member takes the same
            # top-level placement, so dimension 5 is the only place a
            # `(record, projection)` rehydrator can read it back from.
            source_refresh_recency=(
                record.content_generation_path.source_refresh_recency
            ),
            # And what the signal obliged, for a stronger reason again
            # (D-IMPL-117 gap 3): a rehydrator could resolve the deployment's
            # CURRENT debt profile for the same signal and get a plausible
            # answer, which is the substitution D-IMPL-26 forbids. The value in
            # force at decision time lives on dimension 5 and nowhere else.
            obligation_in_force=record.content_generation_path.obligation_in_force,
        )


def _spawn(
    script: str, stderr_dir: Path, env: dict[str, str] | None = None
) -> tuple[subprocess.Popen[bytes], int]:
    """Spawn a READY-announcing child; wait, bounded, for its line.

    Two failure modes, both visible rather than fatal-by-hanging:

    * A child that DIES before announcing (the D-06 unpaired-fixture
      refusal, for one) closes stdout, so the readline returns empty and
      the raise below names the script and its stderr file.
    * A child that STARTS but never reaches READY — a uvicorn bind that
      stalls, a fixture load that blocks — used to hang this process
      forever, and since this runs in CI it hung the build with no
      diagnostic. `select` bounds the wait at
      `READY_TIMEOUT_SECONDS`, then kills the child and raises.

    The stderr file handle is closed on every path (it was leaked
    outright on the old exception path); the child keeps its own dup of
    the descriptor.
    """
    stderr_path = stderr_dir / f"{Path(script).stem}.stderr"
    with stderr_path.open("wb") as stderr_file:
        proc = subprocess.Popen(
            [sys.executable, str(_EXAMPLE_ROOT / script)],
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            start_new_session=True,
            env=env,
        )
    if proc.stdout is None:  # pragma: no cover - stdout=PIPE was requested
        raise AssertionError(f"{script} was spawned without a stdout pipe")
    try:
        ready, _, _ = select.select(
            [proc.stdout], [], [], READY_TIMEOUT_SECONDS
        )
        if not ready:
            raise AssertionError(
                f"{script} did not announce readiness within "
                f"{READY_TIMEOUT_SECONDS:.0f}s; see {stderr_path}"
            )
        announcement = proc.stdout.readline().decode().strip()
        if not announcement.startswith("READY "):
            raise AssertionError(
                f"{script} did not announce readiness: {announcement!r}; see "
                f"{stderr_path}"
            )
    except BaseException:
        _terminate(proc)
        raise
    return proc, int(announcement.split()[1])


def _terminate(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=TERMINATE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


async def _mcp_call_text(url: str, token: str, tool: str, arguments: dict) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments)
    if result.isError:
        raise AssertionError(f"{tool} refused: {result.content}")
    return "".join(getattr(block, "text", "") for block in result.content)


async def _mcp_probe(
    url: str,
    token: str,
    resource_uri: str,
    tool: str,
    arguments: dict,
) -> tuple[str, str, frozenset[str]]:
    """One authenticated session, three reads (D-07 + allowlist visibility).

    Returns the templated Experience resource's text (``read_resource`` —
    the ``canonical_bytes(servable.product)`` path in
    ``ccf_runtime.mcp.experience``), the ``get_context`` tool's text (the
    serve path), and the set of tool names ``tools/list`` advertises.
    """
    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            resource = await session.read_resource(AnyUrl(resource_uri))
            result = await session.call_tool(tool, arguments)
            listing = await session.list_tools()
    if result.isError:
        raise AssertionError(f"{tool} refused: {result.content}")
    resource_text = "".join(
        getattr(block, "text", "") for block in resource.contents
    )
    tool_text = "".join(
        getattr(block, "text", "") for block in result.content
    )
    return resource_text, tool_text, frozenset(t.name for t in listing.tools)


def _run_leg(script: str, env: dict[str, str]) -> str:
    completed = subprocess.run(
        [sys.executable, str(_EXAMPLE_ROOT / script)],
        env=env,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"{script} exited {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed.stdout


def _leg_environments(
    *,
    base_env: dict[str, str],
    replay_port: int | None,
    live: bool,
    experience: Any,
) -> dict[str, dict[str, str]]:
    """Per-leg env contracts. Offline: base-URL redirect is the ONLY switch
    (D-09) and fixture labels name the recorded conversations; live: the
    redirects are ABSENT, real keys come from the caller's environment, and
    model names come from ``artifacts/experience.yaml`` ``live_mode``."""
    anthropic_env = dict(base_env)
    adk_env = dict(base_env)
    if live:
        for env in (anthropic_env, adk_env):
            env.pop("ANTHROPIC_BASE_URL", None)
            env.pop("GOOGLE_GEMINI_BASE_URL", None)
        anthropic_env["CCF_EXAMPLE_MODEL"] = experience["live_mode"][
            "anthropic_model"
        ]
        adk_env["CCF_EXAMPLE_GEMINI_MODEL"] = experience["live_mode"][
            "gemini_model"
        ]
    else:
        if replay_port is None:
            raise AssertionError(
                "offline mode needs the replay server's port; none was bound"
            )
        redirect = f"http://127.0.0.1:{replay_port}"
        recorded_request = json.loads(
            (FIXTURES / "anthropic-00-request.json").read_text(
                encoding="utf-8"
            )
        )
        anthropic_env.update(
            ANTHROPIC_BASE_URL=redirect,
            ANTHROPIC_API_KEY="ci-replay",
            CCF_EXAMPLE_MODEL=recorded_request["model"],
        )
        adk_env.update(
            GOOGLE_GEMINI_BASE_URL=redirect,
            GOOGLE_API_KEY="ci-replay",
            CCF_EXAMPLE_GEMINI_MODEL=GEMINI_FIXTURE_LABEL,
        )
    return {"bare": dict(base_env), "anthropic": anthropic_env, "adk": adk_env}


def _assert_bad_token_refused(url: str, revoked_token: str) -> None:
    """D-12/T-13.1-11: the revoked token from the artifact table gets 401."""
    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {revoked_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        timeout=30.0,
    )
    if response.status_code != 401:
        raise AssertionError(
            f"revoked token was not refused with 401 (got "
            f"{response.status_code}): the auth path has regressed"
        )


def _assert_zero_ccf_imports() -> None:
    """D-06: static grep over the client legs — the charter, mechanically."""
    pattern = re.compile(r"^(import|from) (ccf|ccf_runtime)", re.MULTILINE)
    offenders = [
        path.name
        for path in sorted(_EXAMPLE_ROOT.glob("client_*.py"))
        if pattern.search(path.read_text(encoding="utf-8"))
    ]
    if offenders:
        raise AssertionError(f"CCF imports found in client legs: {offenders}")


def _assert_seven_heading_readme() -> None:
    """D-17/D-08: the seven Phase-13 template headings, by name, in order."""
    readme = (_EXAMPLE_ROOT / "README.md").read_text(encoding="utf-8")
    headings = tuple(
        line[len("## "):].strip()
        for line in readme.splitlines()
        if line.startswith("## ")
    )
    if len(headings) != len(README_HEADINGS):
        raise AssertionError(
            f"README.md has {len(headings)} '## ' headings; the template "
            f"requires exactly {len(README_HEADINGS)}: {headings}"
        )
    for position, (actual, expected) in enumerate(
        zip(headings, README_HEADINGS), start=1
    ):
        if actual != expected:
            raise AssertionError(
                f"README.md heading {position} is {actual!r}; the Phase-13 "
                f"template requires {expected!r} at that position (D-08)"
            )


def _assert_byte_equal_reproduction(
    served_bytes: bytes,
    *,
    serve_request_label: str,
    booted: BootedFabric,
    registry: ControlPlaneRegistry,
) -> None:
    """D-16/T-13.1-12: resolve the serve record from the store, replay it
    against a fabric rebuilt from the same artifacts, and require the
    reproduced product's canonical bytes to equal the served bytes.

    ``booted`` is this process's own replica — booted from the SAME
    ``artifacts/manifest.yaml`` ``serve.py`` booted from and ingested from the
    same event batch. Content-derived Control Plane versions and
    content-hashed entity URIs are what make the replica's state the recorded
    state (D-IMPL-38); ``registry`` is the Control Plane those pins landed in,
    and the engine resolves the record's bindings against it at their exact
    recorded versions.

    ``serve_request_label`` names WHICH serve produced ``served_bytes``
    (``serve.get_context_request_label``). It is not decoration: this
    deployment records a ``ServeRequestRecord`` for the templated resource
    read as well as for the ``get_context`` call, both under the same
    client identity. Taking ``versions[-1]`` compared ``served_bytes``
    against whichever record happened to land last, which lined up only
    because ``_mcp_probe`` calls ``read_resource`` before ``call_tool``
    (IN-04) — an invisible coupling that stays green today (one product,
    identical bytes) and breaks silently the moment the example grows a
    second product."""
    governance = cast(
        DeclaredArtifact, booted.artifacts["product-governance"]
    ).declaration
    tokens = cast(DeclaredArtifact, booted.artifacts["tokens"]).declaration

    store = FileArtifactStore(root=_EXAMPLE_ROOT / ".store")

    # The serve event and the decision record name each other (D-13): each
    # ServeRequestRecord for the presenting client identity carries the
    # exact versioned URI of the replay record ITS delivery landed under.
    # Names move; the resolved address does not (D-IMPL-26). Select the
    # record by the serve it describes rather than by store position, so
    # the D-16 comparison is bound to the serve that produced these bytes.
    active = next(
        entry for entry in tokens["tokens"] if entry["status"] == "active"
    )
    versions = store.versions(
        tenant_id=booted.tenant_id,
        artifact_class=governance["serve_request_class"],
        name=active["client_id"],
    )
    if not versions:
        raise AssertionError("no ServeRequestRecord landed in the ArtifactStore")
    matching = [
        record
        for record in (
            resolve_artifact(
                store=store,
                content_address=address,
                contract=fabric.ServeRequestRecord,
            )
            for address in versions
        )
        if record.request == serve_request_label
    ]
    if not matching:
        raise AssertionError(
            "no ServeRequestRecord in the ArtifactStore describes the serve "
            f"that produced the compared bytes ({serve_request_label!r}); "
            "the D-16 reproduction has nothing to bind to"
        )
    # Newest among the records for THIS serve — the probe issues one
    # get_context call, so this is that call's record.
    serve_request = matching[-1]
    record_address = store.resolve_uri(uri=serve_request.replay_uri)

    outcome = replay(
        record_address=record_address,
        store=store,
        reader=booted.handle.reader,
        control_plane=registry,
        environment=HelloReplayEnvironment(booted=booted),
    )
    if canonical_bytes(outcome.product) != served_bytes:
        raise AssertionError(
            "the replayed product's canonical bytes differ from the bytes the "
            "front door served — D-16 reproduction failed"
        )


def main() -> int:
    started = time.monotonic()  # D-09: soft annotation only, never a gate
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--legs",
        default=",".join(ALL_LEGS),
        help="comma-separated subset of: bare,anthropic,adk",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="run LLM legs against the real vendor APIs (never CI, D-11): "
        "no replay server, base-URL redirects unset, live model names "
        "from artifacts/experience.yaml, real keys from your environment",
    )
    args = parser.parse_args()
    legs = tuple(leg.strip() for leg in args.legs.split(",") if leg.strip())
    unknown = set(legs) - set(ALL_LEGS)
    if unknown:
        raise AssertionError(f"unknown legs: {sorted(unknown)}")

    serve_proc: subprocess.Popen[bytes] | None = None
    replay_proc: subprocess.Popen[bytes] | None = None
    with tempfile.TemporaryDirectory(prefix="ccf-ext00-run-") as scratch:
        # This process's replica of the fabric, booted from the SAME manifest
        # `serve.py` boots from. It supplies two things at once: the parsed
        # artifact set every assertion below reads its expectations from, and
        # the graph PASS 8 replays the recorded decision against. Its handle
        # stays open for the whole run and is closed in the outer `finally`.
        registry = ControlPlaneRegistry()
        booted = load_and_boot(
            fabric.MANIFEST,
            registry=registry,
            connection={"database_path": str(Path(scratch) / "replica.sqlite3")},
        )
        try:
            for envelope in cast(
                SignalBatch, booted.artifacts["events"]
            ).envelopes:
                booted.handle.worker.ingest(envelope)

            experience = cast(
                DeclaredArtifact, booted.artifacts["experience"]
            ).declaration
            focus = cast(
                DeclaredArtifact, booted.artifacts["focus"]
            ).declaration
            declared_class = cast(
                ProductClassDeclaration, booted.artifacts["product-class"]
            )
            tokens = cast(
                DeclaredArtifact, booted.artifacts["tokens"]
            ).declaration
            active = next(
                entry for entry in tokens["tokens"] if entry["status"] == "active"
            )
            revoked = next(
                entry for entry in tokens["tokens"] if entry["status"] == "revoked"
            )

            # The two child processes and every assertion that needs them
            # alive. Terminated in `finally` with a kill fallback (T-13.1-14).
            try:
                serve_proc, serve_port = _spawn("serve.py", Path(scratch))
                url = f"http://127.0.0.1:{serve_port}/mcp"
                replay_port: int | None = None
                if not args.live:
                    # D-08: the Gemini API carries the model in the URL, not
                    # the body, so the replay server cannot read the expected
                    # model off the (body-only) recorded request. It is handed
                    # the SAME label the adk leg is given below, through this
                    # env seam — the `*_BASE_URL` pattern, one level up.
                    replay_proc, replay_port = _spawn(
                        "replay_server.py",
                        Path(scratch),
                        env={
                            **os.environ,
                            "CCF_EXT00_GEMINI_MODEL": GEMINI_FIXTURE_LABEL,
                        },
                    )

                base_env = {
                    **os.environ,
                    "CCF_MCP_URL": url,
                    "CCF_TOKEN": active["token"],
                    # Entity refs in the served payload are content-hashed and
                    # not client-discoverable, so the harness derives the
                    # deployment values from the artifacts (plan-03 contract).
                    "CCF_EXAMPLE_TENANT": booted.tenant_id,
                    "CCF_EXAMPLE_ENTITY": focus["entity_ref"],
                    # The question each LLM leg asks, from the artifact rather
                    # than from a default inside the client. Phase 20's
                    # tightened `cinv01a-prompt-shape` refuses a literal
                    # reaching a model-instruction sink, and the two legs used
                    # to reach theirs through an `os.environ.get` fallback —
                    # a prompt in code wearing an env var as a hat (§6.4).
                    # The legs now read this as REQUIRED, so a driver that
                    # forgets it fails loudly instead of running a hidden one.
                    "CCF_EXAMPLE_QUESTION": experience["client_question"],
                }
                leg_env = _leg_environments(
                    base_env=base_env,
                    replay_port=replay_port,
                    live=args.live,
                    experience=experience,
                )

                outputs: dict[str, str] = {}
                for leg in legs:
                    outputs[leg] = _run_leg(f"client_{leg}.py", leg_env[leg])
                print(f"PASS 1: client legs exit 0 ({', '.join(legs)})")

                _assert_bad_token_refused(url, revoked["token"])
                print("PASS 2: revoked token refused with 401 (D-12)")

                _assert_zero_ccf_imports()
                print("PASS 3: zero CCF imports in client_*.py (D-06)")

                _assert_seven_heading_readme()
                print(
                    "PASS 4: README headings match the seven Phase-13 template "
                    "names in order (D-17/D-08)"
                )

                # The arguments the deployment's get_context tool takes. Entity
                # refs in the served payload are content-hashed and not
                # client-discoverable, so the harness derives them from the
                # artifacts (plan-03 contract). Resolved HERE, above the D-15
                # block, because the fallback below needs them too (WR-04).
                get_context_arguments = {
                    "tenant": booted.tenant_id,
                    "entity": focus["entity_ref"],
                }

                # D-15: lineage and the five-dimension replay record were
                # retrieved OVER MCP. The bare leg carries the demonstration;
                # when it is deselected, a direct MCP read stands in.
                if "bare" in outputs:
                    evidence = outputs["bare"]
                else:
                    # WR-04: get_replay_record is per-client (WR-06) and refuses
                    # a client that has served nothing. Every selected leg
                    # happens to call get_context first, so this stand-in used
                    # to work only by accident of leg ordering — and with the
                    # legs deselected entirely (`--legs ""`) it failed with
                    # "get_replay_record refused", a diagnostic that points at
                    # the Experience surface rather than at the real cause.
                    # Make the dependency explicit: this branch serves itself
                    # the product whose record it is about to read.
                    asyncio.run(
                        _mcp_call_text(
                            url,
                            active["token"],
                            experience["tools"]["get_context"]["name"],
                            get_context_arguments,
                        )
                    )
                    evidence = asyncio.run(
                        _mcp_call_text(
                            url,
                            active["token"],
                            experience["tools"]["get_lineage"]["name"],
                            {},
                        )
                    ) + asyncio.run(
                        _mcp_call_text(
                            url,
                            active["token"],
                            experience["tools"]["get_replay_record"]["name"],
                            {},
                        )
                    )
                if "operators_invoked" not in evidence:
                    raise AssertionError("no lineage retrieved over MCP")
                if "content_generation_path" not in evidence:
                    raise AssertionError("no replay record retrieved over MCP")
                print("PASS 5: lineage + replay record retrieved over MCP (D-15)")

                # One authenticated session: the templated Experience resource,
                # the get_context tool (this also captures the exact bytes the
                # front door serves, for D-16), and tools/list.
                resource_uri = fabric.experience_product_uri(
                    tenant=booted.tenant_id,
                    product_class=declared_class.schema_name,
                    version=declared_class.schema_version,
                )
                # IN-04: name the serve whose bytes PASS 8 compares, so the D-16
                # assertion selects that serve's record explicitly rather than
                # depending on _mcp_probe's internal read order.
                get_context_label = fabric.get_context_request_label(
                    tenant=get_context_arguments["tenant"],
                    entity=get_context_arguments["entity"],
                )
                resource_text, served_text, advertised = asyncio.run(
                    _mcp_probe(
                        url,
                        active["token"],
                        resource_uri,
                        experience["tools"]["get_context"]["name"],
                        get_context_arguments,
                    )
                )

                # D-07: both serve paths — the templated resource
                # (canonical_bytes in ccf_runtime.mcp.experience) and the
                # get_context tool (the deployment's serve path) — must yield
                # byte-identical product serializations.
                if resource_text.encode("utf-8") != served_text.encode("utf-8"):
                    raise AssertionError(
                        "the Experience resource path and the get_context tool "
                        "serve different bytes for the same product — dual "
                        "serve-path serialization divergence (D-07)"
                    )
                print(
                    "PASS 6: resource path and get_context serve identical "
                    "bytes (D-07)"
                )

                # Allowlist visibility: tools/list advertises exactly the
                # artifact-carried allowlist — nothing filtered, nothing extra.
                allowlist = frozenset(experience["tool_allowlist"])
                if advertised != allowlist:
                    raise AssertionError(
                        f"tools/list advertises {sorted(advertised)} but the "
                        f"artifact allowlist declares {sorted(allowlist)} (D-05)"
                    )
                print(
                    "PASS 7: advertised tools equal the artifact allowlist "
                    "(D-05)"
                )
            finally:
                _terminate(serve_proc)
                _terminate(replay_proc)

            _assert_byte_equal_reproduction(
                served_text.encode("utf-8"),
                serve_request_label=get_context_label,
                booted=booted,
                registry=registry,
            )
            print("PASS 8: fabric-side byte-equal reproduction (D-16)")
        finally:
            booted.handle.close()

    docs_leg = " + docs-only .mcp.json leg" if not args.live else ""
    print(f"duration: {time.monotonic() - started:.1f}s")
    print(
        "examples/external/00-hello-context: OK "
        f"({len(legs)} runnable legs{docs_leg}; 8 assertions)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
