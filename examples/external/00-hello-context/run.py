"""examples/external/00-hello-context — one command, four legs, six assertions.

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
4. **Seven-heading README (D-17).** Exactly seven ``## `` headings, per the
   Phase-13 D-02 template; the ``.mcp.json`` docs-only leg lives there.
5. **D-15 retrieval.** The bare leg's output shows lineage AND the
   five-dimension Decision Replay record (whitepaper §7.10) retrieved over
   the same authenticated MCP surface the product came from.
6. **D-16 byte-equal reproduction (T-13.1-12).** The serve-time replay
   record is resolved from the file-backed ArtifactStore (CLAUDE.md §7.4)
   at its exact content address, replayed through
   ``ccf.replay.engine.replay`` against a rebuilt-from-artifacts fabric,
   and the reproduced product's canonical bytes equal the bytes the front
   door actually served.

Every domain and deployment value comes from ``artifacts/*.yaml`` or the
versioned ``fixtures/`` (CLAUDE.md §6.4); this file interprets. Readiness
is a blocking ``readline()`` on each child's ``READY <port>`` line — no
sleeps. Children are terminated in ``finally`` with a kill fallback
(T-13.1-14; example-04 precedent).

Run it: ``make example-ext-00``. Live variants (never CI, D-11):
``make example-ext-00-live-anthropic`` / ``make example-ext-00-live-adk``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

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
from mcp import ClientSession  # noqa: E402
from mcp.client.streamable_http import streamablehttp_client  # noqa: E402

import serve as fabric  # noqa: E402  — the sibling fabric-side module

from ccf.artifacts.file_store import FileArtifactStore  # noqa: E402
from ccf.boot import boot  # noqa: E402
from ccf.contracts.canonical import canonical_bytes  # noqa: E402
from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: E402
from ccf.products.contract import (  # noqa: E402
    ContextProductContract,
    ProductLineage,
)
from ccf.projection.engine import OperatorRegistry  # noqa: E402
from ccf.replay.engine import replay, resolve_artifact  # noqa: E402
from ccf.replay.record import DecisionReplayRecord  # noqa: E402

from datetime import timedelta  # noqa: E402

ARTIFACTS = _EXAMPLE_ROOT / "artifacts"
FIXTURES = _EXAMPLE_ROOT / "fixtures"
TERMINATE_TIMEOUT_SECONDS = 10.0
ALL_LEGS = ("bare", "anthropic", "adk")

#: Fixture-matching label for the Gemini leg. The Anthropic label is read
#: from the recorded request body itself; the Gemini Generate-Content API
#: carries the model in the URL path, which the recorded request bodies do
#: not include, so the label the CI harness passes is stated here exactly
#: as ``fixtures/README.md`` documents it. It names a fixture, never a
#: deployment model — live model names live in ``artifacts/experience.yaml``.
GEMINI_FIXTURE_LABEL = "gemini-fixture"


class HelloReplayEnvironment:
    """The deployment side of the replay seam (``ReplayEnvironment``).

    The projection, operators, and product envelope are rebuilt from the
    SAME artifacts ``serve.py`` assembled from, and the engine VERIFIES
    every one of them against the record rather than trusting this class
    (example-06 pattern; whitepaper §7.10; D-IMPL-26/44).
    """

    def __init__(
        self,
        *,
        ontology: Any,
        control: Any,
        product_doc: Any,
        reader: Any,
        policy_version: str,
    ) -> None:
        self._ontology = ontology
        self._control = control
        self._product_doc = product_doc
        self._reader = reader
        self._policy_version = policy_version

    def _operators(self) -> OperatorRegistry:
        tenant_id = self._ontology["tenant_id"]
        boundary = fabric._instant(
            self._control["decision"]["temporal_boundary"]
        )
        corpus_attribute = self._ontology[
            "similarity_corpus_attribute_by_class"
        ]
        view = self._reader.as_of(tenant_id=tenant_id, at=boundary)
        corpus = {
            (tenant_id, record.claim.entity_uri): record.claim.attributes[
                corpus_attribute[record.claim.entity_class]
            ]
            for record in view.entities
            if record.claim.entity_class in corpus_attribute
        }
        return fabric._operators(
            ontology=self._ontology,
            params=self._control["operator_parameters"],
            policy_version=self._policy_version,
            corpus=corpus,
        )

    def resolve_plan(self, *, plan_id: str) -> Any:
        declared = self._product_doc["product_class"]
        if plan_id != declared["plan_id"]:
            raise LookupError(plan_id)
        return fabric.CreditContextPlan(
            plan_id=declared["plan_id"], required=self._operators().keys()
        )

    def resolve_operators(
        self, *, operator_keys: tuple[str, ...]
    ) -> OperatorRegistry:
        return self._operators()

    def rehydrate_product(
        self, *, record: DecisionReplayRecord, projection: Any
    ) -> ContextProductContract:
        declared = self._product_doc["product_class"]
        now = fabric._instant(self._control["decision"]["now"])
        return ContextProductContract(
            schema_name=declared["schema_name"],
            schema_version=declared["schema_version"],
            plan_id=projection.plan_id,
            tenant_id=record.tenant_id,
            temporal_boundary=record.context_fabric_snapshot.temporal_boundary,
            expires_at=now
            + timedelta(seconds=declared["product_ttl_seconds"]),
            ttl_anchor=declared["ttl_anchor"],
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
            payload=projection.payload,
        )


def _spawn(script: str, stderr_dir: Path) -> tuple[subprocess.Popen[bytes], int]:
    """Spawn a READY-announcing child; block on its announcement line."""
    stderr_path = stderr_dir / f"{Path(script).stem}.stderr"
    proc = subprocess.Popen(
        [sys.executable, str(_EXAMPLE_ROOT / script)],
        stdout=subprocess.PIPE,
        stderr=stderr_path.open("wb"),
        start_new_session=True,
    )
    assert proc.stdout is not None
    announcement = proc.stdout.readline().decode().strip()
    if not announcement.startswith("READY "):
        raise AssertionError(
            f"{script} did not announce readiness: {announcement!r}; see "
            f"{stderr_path}"
        )
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
    assert not result.isError, f"{tool} refused: {result.content}"
    return "".join(getattr(block, "text", "") for block in result.content)


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
        assert replay_port is not None
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
    assert response.status_code == 401, (
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
    assert not offenders, f"CCF imports found in client legs: {offenders}"


def _assert_seven_heading_readme() -> None:
    """D-17: exactly seven `## ` headings, per the Phase-13 D-02 template."""
    readme = (_EXAMPLE_ROOT / "README.md").read_text(encoding="utf-8")
    headings = [
        line for line in readme.splitlines() if line.startswith("## ")
    ]
    assert len(headings) == 7, (
        f"README.md has {len(headings)} '## ' headings; the template "
        f"requires exactly 7: {headings}"
    )


def _assert_byte_equal_reproduction(served_bytes: bytes) -> None:
    """D-16/T-13.1-12: resolve the serve record from the store, replay it
    against a fabric rebuilt from the same artifacts, and require the
    reproduced product's canonical bytes to equal the served bytes."""
    ontology = fabric._load("ontology.yaml")
    events = fabric._load("events.yaml")
    control = fabric._load("controlplane.yaml")
    product_doc = fabric._load("product.yaml")
    tokens = fabric._load("tokens.yaml")
    tenant_id: str = ontology["tenant_id"]
    keys = control["keys"]

    store = FileArtifactStore(root=_EXAMPLE_ROOT / ".store")

    # The serve event and the decision record name each other (D-13): the
    # newest ServeRequestRecord for the presenting client identity carries
    # the exact versioned URI of the replay record its delivery landed
    # under. Names move; the resolved address does not (D-IMPL-26).
    active = next(
        entry for entry in tokens["tokens"] if entry["status"] == "active"
    )
    versions = store.versions(
        tenant_id=tenant_id,
        artifact_class=control["artifacts"]["serve_request_class"],
        name=active["client_id"],
    )
    assert versions, "no ServeRequestRecord landed in the ArtifactStore"
    serve_request = resolve_artifact(
        store=store,
        content_address=versions[-1],
        contract=fabric.ServeRequestRecord,
    )
    record_address = store.resolve_uri(uri=serve_request.replay_uri)

    # Rebuild the fabric from the same artifacts serve.py booted from —
    # content-derived Control Plane versions and content-hashed entity URIs
    # make the replica's state the recorded state (D-IMPL-38).
    registry = ControlPlaneRegistry()
    spec_version = registry.register(
        keys["resolution_spec"], fabric._resolution_spec(ontology)
    )
    policy_version = registry.register(
        keys["policy_bundle"], control["policy_bundle"]
    )
    with tempfile.TemporaryDirectory(prefix="ccf-ext00-replay-") as scratch:
        handle = boot(
            database_path=Path(scratch) / "replica.sqlite3",
            registry=registry,
            resolution_spec_key=keys["resolution_spec"],
            resolution_spec_version=spec_version,
            policy_bundle_key=keys["policy_bundle"],
            policy_bundle_version=policy_version,
        )
        try:
            for envelope in fabric._envelopes(ontology, events):
                handle.worker.ingest(envelope)
            outcome = replay(
                record_address=record_address,
                store=store,
                reader=handle.reader,
                control_plane=registry,
                environment=HelloReplayEnvironment(
                    ontology=ontology,
                    control=control,
                    product_doc=product_doc,
                    reader=handle.reader,
                    policy_version=policy_version,
                ),
            )
        finally:
            handle.close()
    assert canonical_bytes(outcome.product) == served_bytes, (
        "the replayed product's canonical bytes differ from the bytes the "
        "front door served — D-16 reproduction failed"
    )


def main() -> int:
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
    assert not unknown, f"unknown legs: {sorted(unknown)}"

    ontology = fabric._load("ontology.yaml")
    product_doc = fabric._load("product.yaml")
    experience = fabric._load("experience.yaml")
    tokens = fabric._load("tokens.yaml")
    active = next(
        entry for entry in tokens["tokens"] if entry["status"] == "active"
    )
    revoked = next(
        entry for entry in tokens["tokens"] if entry["status"] == "revoked"
    )

    serve_proc: subprocess.Popen[bytes] | None = None
    replay_proc: subprocess.Popen[bytes] | None = None
    with tempfile.TemporaryDirectory(prefix="ccf-ext00-run-") as scratch:
        try:
            serve_proc, serve_port = _spawn("serve.py", Path(scratch))
            url = f"http://127.0.0.1:{serve_port}/mcp"
            replay_port: int | None = None
            if not args.live:
                replay_proc, replay_port = _spawn(
                    "replay_server.py", Path(scratch)
                )

            import os

            base_env = {
                **os.environ,
                "CCF_MCP_URL": url,
                "CCF_TOKEN": active["token"],
                # Entity refs in the served payload are content-hashed and
                # not client-discoverable, so the harness derives the
                # deployment values from the artifacts (plan-03 contract).
                "CCF_EXAMPLE_TENANT": ontology["tenant_id"],
                "CCF_EXAMPLE_ENTITY": product_doc["focus"]["entity_ref"],
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
            print("PASS 4: README has exactly seven '## ' headings (D-17)")

            # D-15: lineage and the five-dimension replay record were
            # retrieved OVER MCP. The bare leg carries the demonstration;
            # when it is deselected, a direct MCP read stands in.
            if "bare" in outputs:
                evidence = outputs["bare"]
            else:
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
            assert "operators_invoked" in evidence, (
                "no lineage retrieved over MCP"
            )
            assert "content_generation_path" in evidence, (
                "no replay record retrieved over MCP"
            )
            print("PASS 5: lineage + replay record retrieved over MCP (D-15)")

            # Capture the exact bytes the front door serves, for D-16.
            served_text = asyncio.run(
                _mcp_call_text(
                    url,
                    active["token"],
                    experience["tools"]["get_context"]["name"],
                    {
                        "tenant": ontology["tenant_id"],
                        "entity": product_doc["focus"]["entity_ref"],
                    },
                )
            )
        finally:
            _terminate(serve_proc)
            _terminate(replay_proc)

        _assert_byte_equal_reproduction(served_text.encode("utf-8"))
        print("PASS 6: fabric-side byte-equal reproduction (D-16)")

    docs_leg = " + docs-only .mcp.json leg" if not args.live else ""
    print(
        "examples/external/00-hello-context: OK "
        f"({len(legs)} runnable legs{docs_leg}; 6 assertions)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
