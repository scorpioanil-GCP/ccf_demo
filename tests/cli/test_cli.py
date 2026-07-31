"""The `ccf` CLI dispatches the ruled noun-verb inventory (07-11 Task 1).

Written before the implementation per the TDD discipline. The claims:

**Inventory.** Every ruled noun-verb pair parses and dispatches — workflow
invoke/status/resume, hitl list/decide, replay query/resolve, config
keys/versions/resolve, agent declare/list/show/versions, skill
list/grant/revoke, artifact inspect/put, product get (D-IMPL-22).

**No inline definitions.** ``ccf agent declare`` takes an artifact file;
no inline definition flag exists to parse (T-07-29; No-Hardcoding §6.4).

**Shared bundle, by type.** ``--local`` constructs the SAME
``ApiDependencies`` type ``create_app`` consumes — asserted by type, not
by intent (T-07-27; the Codex shared-abstraction finding) — and the
injected path produces output identical to a real HTTP server over the
same bundle.

**Exit codes.** Typed refusals are nonzero with the refusal body printed;
wiring errors are a distinct nonzero code on stderr.

**No hardcoded deployment URL.** The CLI source names no ``http(s)://``
deployment URL (CINV-01: the base URL is flag/env-injected).
"""

from __future__ import annotations

import json
import socket
import threading
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.contracts.canonical import content_hash

from cli.conftest import Fabric, run_cli

CLI_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "runtime"
    / "ccf_runtime"
    / "cli"
)

#: Every ruled noun-verb pair with placeholder arguments — the inventory
#: claim is that each parses to a dispatchable command (D-IMPL-22).
INVENTORY: tuple[tuple[str, ...], ...] = (
    ("agent", "declare", "--key", "k", "--file", "f"),
    ("agent", "list"),
    ("agent", "show", "--key", "k", "--version", "1.0.0"),
    ("agent", "versions", "--key", "k"),
    ("skill", "list"),
    ("skill", "grant", "--file", "f"),
    ("skill", "revoke", "--grant-hash", "h", "--actor", "a"),
    (
        "workflow",
        "invoke",
        "--definition-key",
        "k",
        "--definition-version",
        "v",
        "--execution-id",
        "e",
    ),
    (
        "workflow",
        "resume",
        "--definition-key",
        "k",
        "--definition-version",
        "v",
        "--execution-id",
        "e",
        "--decision",
        "d",
    ),
    ("workflow", "status", "--tenant", "t", "--execution-id", "e"),
    ("hitl", "list", "--tenant", "t"),
    ("hitl", "decide", "--file", "f"),
    ("replay", "query", "--content-address", "a"),
    ("replay", "resolve", "--uri", "u"),
    ("artifact", "inspect", "a"),
    ("artifact", "put", "--file", "f"),
    ("product", "get", "--tenant", "t", "--product-class", "c", "--version", "v"),
    ("config", "keys", "--class-id", "c"),
    ("config", "versions", "--key", "k"),
    ("config", "resolve", "--key", "k", "--version", "v"),
)


# --- inventory: every ruled pair parses to a dispatchable command ----------


@pytest.mark.parametrize("argv", INVENTORY, ids=lambda a: " ".join(a[:2]))
def test_ruled_noun_verb_pair_parses(argv: tuple[str, ...]) -> None:
    from ccf_runtime.cli.main import build_parser

    parsed = build_parser().parse_args(list(argv))
    assert getattr(parsed, "build", None) is not None


def test_every_noun_lists_its_verbs_in_help() -> None:
    from ccf_runtime.cli.main import build_parser

    nouns = {argv[0] for argv in INVENTORY}
    parser = build_parser()
    text = parser.format_help()
    for noun in nouns:
        assert noun in text


# --- agent declare: artifact file only, no inline definition flags ---------


def test_agent_declare_refuses_inline_definition_flags() -> None:
    from ccf_runtime.cli.main import build_parser

    parser = build_parser()
    for flag in ("--name", "--archetypes", "--tenant", "--template"):
        with pytest.raises(SystemExit):
            parser.parse_args(
                ["agent", "declare", "--key", "k", "--file", "f", flag, "x"]
            )


def test_agent_declare_takes_an_artifact_file(
    fabric: Fabric,
    deps: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    document = dict(fabric.grants_fixture["agents"]["gated"])
    key = f"acme-bank/agents/cli-{document['name']}"
    artifact_file = tmp_path / "agent.yaml"
    artifact_file.write_text(yaml.safe_dump(document))
    code, out, _ = run_cli(
        ["agent", "declare", "--key", key, "--file", str(artifact_file)],
        capsys,
        dependencies=deps,
    )
    assert code == 0
    version = json.loads(out)["version"]
    code, out, _ = run_cli(
        ["agent", "show", "--key", key, "--version", version],
        capsys,
        dependencies=deps,
    )
    assert code == 0
    assert json.loads(out)["name"] == document["name"]
    code, out, _ = run_cli(["agent", "list"], capsys, dependencies=deps)
    assert code == 0 and key in json.loads(out)
    code, out, _ = run_cli(
        ["agent", "versions", "--key", key], capsys, dependencies=deps
    )
    assert code == 0 and version in json.loads(out)


# --- read verbs dispatch against the same routes any client reaches --------


def test_read_verbs_dispatch(
    fabric: Fabric, deps: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = run_cli(["skill", "list"], capsys, dependencies=deps)
    assert code == 0
    assert "covenant-metrics" in {e["name"] for e in json.loads(out)}

    code, out, _ = run_cli(
        ["hitl", "list", "--tenant", "acme-bank"], capsys, dependencies=deps
    )
    assert code == 0 and json.loads(out) == []

    code, out, _ = run_cli(
        ["config", "keys", "--class-id", "ccf.agent-definition"],
        capsys,
        dependencies=deps,
    )
    assert code == 0 and fabric.auto_agent_key in json.loads(out)

    code, out, _ = run_cli(
        ["config", "versions", "--key", fabric.auto_agent_key],
        capsys,
        dependencies=deps,
    )
    assert code == 0 and fabric.auto_agent_version in json.loads(out)

    code, out, _ = run_cli(
        [
            "config",
            "resolve",
            "--key",
            fabric.auto_agent_key,
            "--version",
            fabric.auto_agent_version,
        ],
        capsys,
        dependencies=deps,
    )
    assert code == 0 and json.loads(out)["name"] == fabric.auto_agent.name

    code, out, _ = run_cli(
        [
            "replay",
            "query",
            "--content-address",
            fabric.replay_ref.content_address,
        ],
        capsys,
        dependencies=deps,
    )
    assert code == 0 and json.loads(out)["tenant_id"] == "acme-bank"

    code, out, _ = run_cli(
        ["replay", "resolve", "--uri", fabric.replay_ref.uri],
        capsys,
        dependencies=deps,
    )
    assert code == 0 and json.loads(out)["tenant_id"] == "acme-bank"

    code, out, _ = run_cli(
        ["artifact", "inspect", fabric.replay_ref.content_address],
        capsys,
        dependencies=deps,
    )
    assert code == 0 and json.loads(out)["tenant_id"] == "acme-bank"

    address = fabric.product_address
    code, out, _ = run_cli(
        [
            "product",
            "get",
            "--tenant",
            address.tenant,
            "--product-class",
            address.product_class,
            "--version",
            address.version,
        ],
        capsys,
        dependencies=deps,
    )
    assert code == 0 and json.loads(out)["tenant_id"] == address.tenant


# --- workflow: invoke / status / resume ------------------------------------


def test_workflow_invoke_status_resume(
    fabric: Fabric, deps: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    key, version = fabric.refresh
    code, out, _ = run_cli(
        [
            "workflow",
            "invoke",
            "--definition-key",
            key,
            "--definition-version",
            version,
            "--execution-id",
            "cli-refresh-1",
        ],
        capsys,
        dependencies=deps,
    )
    assert code == 0 and json.loads(out)["terminal_state"]

    gate_key, gate_version = fabric.covenant
    code, out, _ = run_cli(
        [
            "workflow",
            "invoke",
            "--definition-key",
            gate_key,
            "--definition-version",
            gate_version,
            "--execution-id",
            "cli-covenant-1",
        ],
        capsys,
        dependencies=deps,
    )
    assert code == 0
    suspended = json.loads(out)
    assert suspended["gate"]

    code, out, _ = run_cli(
        [
            "workflow",
            "status",
            "--tenant",
            suspended["tenant"],
            "--execution-id",
            "cli-covenant-1",
        ],
        capsys,
        dependencies=deps,
    )
    assert code == 0 and json.loads(out)["status"] == "suspended"

    # an undeclared decision is a typed refusal → exit 1, body printed
    code, out, _ = run_cli(
        [
            "workflow",
            "resume",
            "--definition-key",
            gate_key,
            "--definition-version",
            gate_version,
            "--execution-id",
            "cli-covenant-1",
            "--decision",
            "no-such-transition",
        ],
        capsys,
        dependencies=deps,
    )
    assert code == 1 and "declared transition" in out


# --- hitl decide travels the typed authority path --------------------------


def test_hitl_decide_submits_the_typed_action(
    fabric: Fabric,
    deps: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    submission = {
        "event_key": "acme-bank/cli-covenant-1/gate",
        "tenant": "acme-bank",
        "action": "approve",
        "principal": {
            "approver": {
                "subject_id": "risk-officer-7",
                "identity_provider_ref": "idp:acme-sso",
            },
            "authentication": {
                "method": "sso",
                "assurance_level": "aal2",
                "session_ref": "session-1",
            },
            "action_time": "2026-07-30T12:00:00+00:00",
            "product_content_hash": "0" * 64,
        },
        "annotation": None,
    }
    action_file = tmp_path / "action.yaml"
    action_file.write_text(yaml.safe_dump(submission))
    code, _, _ = run_cli(
        ["hitl", "decide", "--file", str(action_file)],
        capsys,
        dependencies=deps,
    )
    assert code == 0
    recorded = fabric.hitl.submissions(tenant="acme-bank")
    assert submission["event_key"] in {s.event_key for s in recorded}


def test_hitl_decide_output_states_submitted_with_disposition(
    fabric: Fabric,
    deps: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """D-IMPL-62 hardening: the CLI output states ``submitted`` — never
    implies resolution — and carries the honest disposition state."""
    submission = {
        "event_key": "acme-bank/cli-receipt-1/gate",
        "tenant": "acme-bank",
        "action": "approve",
        "principal": {
            "approver": {
                "subject_id": "risk-officer-7",
                "identity_provider_ref": "idp:acme-sso",
            },
            "authentication": {
                "method": "sso",
                "assurance_level": "aal2",
                "session_ref": "session-1",
            },
            "action_time": "2026-07-30T12:00:00+00:00",
            "product_content_hash": "0" * 64,
        },
        "annotation": None,
    }
    action_file = tmp_path / "receipt-action.yaml"
    action_file.write_text(yaml.safe_dump(submission))
    code, out, _ = run_cli(
        ["hitl", "decide", "--file", str(action_file)],
        capsys,
        dependencies=deps,
    )
    assert code == 0
    receipt = json.loads(out)
    assert receipt["status"] == "submitted"
    assert set(receipt) == {
        "status",
        "submission",
        "event_pending",
        "submissions_for_event",
    }
    assert receipt["event_pending"] is False
    assert receipt["submission"]["event_key"] == submission["event_key"]


# --- skill grant / revoke through the governed ledger ----------------------


def test_skill_grant_and_revoke(
    fabric: Fabric,
    deps: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    grant = dict(fabric.grants_fixture["grants"]["metrics_tool"])
    grant["agent_definition_hash"] = content_hash(fabric.auto_agent)
    request = {
        "grant": grant,
        "definition_key": fabric.auto_agent_key,
        "definition_version": fabric.auto_agent_version,
        "actor": fabric.actor,
    }
    grant_file = tmp_path / "grant.yaml"
    grant_file.write_text(yaml.safe_dump(request))
    code, out, _ = run_cli(
        ["skill", "grant", "--file", str(grant_file)],
        capsys,
        dependencies=deps,
    )
    assert code == 0
    grant_hash = json.loads(out)["grant_hash"]
    assert grant_hash

    code, _, _ = run_cli(
        ["skill", "revoke", "--grant-hash", grant_hash, "--actor", fabric.actor],
        capsys,
        dependencies=deps,
    )
    assert code == 0

    # revoking a revoked grant is a typed 4xx → exit 1
    code, out, _ = run_cli(
        ["skill", "revoke", "--grant-hash", grant_hash, "--actor", fabric.actor],
        capsys,
        dependencies=deps,
    )
    assert code == 1


# --- exit codes: typed refusal vs wiring error -----------------------------


def test_refusal_exits_1_with_the_body_printed(
    fabric: Fabric,
    deps: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    document = dict(fabric.grants_fixture["agents"]["auto"])
    document["perspective"] = dict(document["perspective"])
    document["perspective"]["selection_params"] = {"changed": "yes"}
    artifact_file = tmp_path / "again.yaml"
    artifact_file.write_text(yaml.safe_dump(document))
    # changed content under an unchanged artifact_version — the registry's
    # typed unbumped-change refusal (D-05), 409 over HTTP
    code, out, _ = run_cli(
        [
            "agent",
            "declare",
            "--key",
            fabric.auto_agent_key,
            "--file",
            str(artifact_file),
        ],
        capsys,
        dependencies=deps,
    )
    assert code == 1
    assert out.strip()  # the refusal body is printed, not swallowed


def test_wiring_error_exits_2_on_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()  # nothing answers here
    code, out, err = run_cli(
        [
            "--base-url",
            f"http://127.0.0.1:{port}",
            "config",
            "keys",
            "--class-id",
            "x",
        ],
        capsys,
    )
    assert code == 2
    assert err.strip() and not out.strip()


def test_missing_base_url_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CCF_BASE_URL", raising=False)
    with pytest.raises(SystemExit):
        run_cli(["config", "keys", "--class-id", "x"], capsys)


# --- --local: the SAME ApiDependencies bundle, by type ---------------------


def test_local_bundle_is_the_api_dependencies_type(tmp_path: Path) -> None:
    from ccf_runtime.cli.local import build_local_dependencies
    from ccf_runtime.http_api.dependencies import ApiDependencies

    bundle = build_local_dependencies(root=tmp_path)
    # by type, not by intent: --local's bundle IS the object create_app
    # consumes (T-07-27; the Codex shared-abstraction finding)
    assert type(bundle) is ApiDependencies


def test_local_flag_runs_without_infra(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = run_cli(
        [
            "--local",
            "--local-root",
            str(tmp_path),
            "config",
            "keys",
            "--class-id",
            "ccf.agent-definition",
        ],
        capsys,
    )
    assert code == 0 and json.loads(out) == []


def test_local_requires_a_root(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        run_cli(["--local", "config", "keys", "--class-id", "x"], capsys)


# --- HTTP-vs-injected equivalence over one real hosted server --------------


def test_local_and_http_paths_produce_identical_output(
    deps: Any, fabric: Fabric, capsys: pytest.CaptureFixture[str]
) -> None:
    import uvicorn

    from ccf_runtime.http_api.app import create_app

    code, injected_out, _ = run_cli(
        ["config", "versions", "--key", fabric.auto_agent_key],
        capsys,
        dependencies=deps,
    )
    assert code == 0

    bound = socket.socket()
    bound.bind(("127.0.0.1", 0))
    bound.listen(16)
    port = bound.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(create_app(deps), log_level="error")
    )
    thread = threading.Thread(
        target=server.run, kwargs={"sockets": [bound]}, daemon=True
    )
    thread.start()
    try:
        while not server.started:
            if not thread.is_alive():
                raise AssertionError("the HTTP server failed to start")
        code, http_out, _ = run_cli(
            [
                "--base-url",
                f"http://127.0.0.1:{port}",
                "config",
                "versions",
                "--key",
                fabric.auto_agent_key,
            ],
            capsys,
        )
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        bound.close()
    assert code == 0
    assert http_out == injected_out


# --- no hardcoded deployment URL in the CLI source -------------------------


def test_cli_source_names_no_deployment_url() -> None:
    for path in CLI_SOURCE.rglob("*.py"):
        text = path.read_text()
        assert "http://" not in text and "https://" not in text, path
