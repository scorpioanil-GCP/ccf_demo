"""The `ccf` CLI dispatches the ruled noun-verb inventory (07-11 Task 1).

Written before the implementation per the TDD discipline. The claims:

**Inventory.** Every ruled noun-verb pair parses and dispatches — workflow
invoke/status/resume, hitl list/submit, replay query/resolve, config
keys/versions/resolve, agent declare/list/show/versions, skill
list/grant/revoke, artifact inspect/put, product get (D-IMPL-22).

**No inline definitions.** ``ccf agent declare`` takes an artifact file;
no inline definition flag exists to parse (T-07-29; No-Hardcoding §6.4).

**Shared bundle, by type.** ``build_local_dependencies`` constructs the
SAME ``ApiDependencies`` type ``create_app`` consumes — asserted by type,
not by intent (T-07-27; the Codex shared-abstraction finding) — and the
injected path produces output identical to a real HTTP server over the
same bundle.

**Governed on every leg (`SEC-002`).** ``create_app`` has no arm that skips
authentication, so the in-process leg these tests drive binds the same five
seams a deployment does and presents a real credential; the equivalence
test hosts a real server built the same way. ``--local`` is **suspended**
and refuses, because the empty Control Plane it mints leaves the SDK's one
deny-by-default authorizer nothing to decide against — asserted below
rather than deleted with the flag.

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

from cli.conftest import CLI_PRINCIPAL, CLI_ROLE, CLI_TOKEN, Fabric, run_cli
from tests.composition import declared_erasure_trust, declared_hitl_policy_key

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
    ("skill", "revoke", "--grant-hash", "h"),  # no --actor (SEC-012)
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
    ("hitl", "submit", "--file", "f"),
    ("replay", "query", "--content-address", "a"),
    ("replay", "resolve", "--uri", "u"),
    ("artifact", "inspect", "a"),
    ("artifact", "put", "--file", "f"),
    ("product", "get", "--tenant", "t", "--product-class", "c", "--version", "v"),
    ("config", "keys", "--class-id", "c"),
    ("config", "versions", "--key", "k"),
    ("config", "resolve", "--key", "k", "--version", "v"),
    ("backends", "list"),
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


def _internal_determination(authority_bundle: Any, uri: str) -> Any:
    """The whole internal refusal a disclosed shell withheld.

    A governed door discloses at the level its entitlement policy states and
    records at full fidelity regardless: dimension 5 of the replay record the
    door minted carries the determination entire. ``uri`` is the shell's own
    ``replay_reference``, so the record read here is the one the caller was
    handed the address of — not one this test went looking for.
    """
    from ccf.products.refusal import RefusalEnvelope
    from ccf.replay.record import DecisionReplayRecord

    store = authority_bundle["refusal_recorder"].artifact_store
    record = DecisionReplayRecord.model_validate_json(
        store.get(content_address=store.resolve_uri(uri=uri))
    )
    return RefusalEnvelope.model_validate_json(
        record.content_generation_path.assembly_refusal
    )


def test_read_verbs_dispatch(
    fabric: Fabric,
    deps: Any,
    authority_bundle: Any,
    capsys: pytest.CaptureFixture[str],
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

    # --- the governed nouns, now that the CLI carries a credential ---------
    #
    # `SEC-002` deleted the posture the assertions below were written against.
    # There is no app built with `acknowledge_insecure_default` any more, no
    # arm of the gate that skips authentication, and no in-process leg that
    # travels anonymously: `ccf` presents a bearer, the door verifies it, and
    # every read here is DECIDED rather than declined for want of an identity.
    # The old `product-door-ungoverned` answer is unreachable by construction
    # — that 503 fires only where no verified grant accompanies the call, and
    # the total gate refuses such a call before any handler exists.
    #
    # The two nouns then part company, and the split is the evidence: a
    # credential is not an entitlement.
    #
    # The evidence nouns are refused, and refused ON THE MERITS. The
    # `D-IMPL-345` dereference boundary's first hold is that the verified
    # `client_id` equals the record's own
    # `perspective_conditioning.principal_id`. This suite's caller is
    # `CLI_PRINCIPAL`; the stored record was determined for another principal,
    # so the read stops at hold 1 — before `authorize` is called and before
    # anything about the target is read.
    for verb in (
        ["replay", "query", "--content-address", fabric.replay_ref.content_address],
        ["replay", "resolve", "--uri", fabric.replay_ref.uri],
        ["artifact", "inspect", fabric.replay_ref.content_address],
    ):
        code, out, err = run_cli(verb, capsys, dependencies=deps)
        # A typed refusal on stdout, not a wiring error on stderr (T-07-26):
        # the door answered, so nothing about it is a wiring problem.
        assert (code, err) == (1, ""), verb
        body = json.loads(out)
        assert body["kind"] == "subject-unavailable", verb
        refusal = body["refusal"]
        # Disclosed at the level this suite's entitlement policy states, and
        # `minimal` withholds the cause: the caller learns that the subject is
        # unavailable, never which hold said so.
        assert refusal["disclosure"] == "minimal", verb
        assert refusal["fields"] == {
            "cause": '"undisclosed"',
            "error_code": '"undisclosed"',
        }, verb
        # Recorded, not merely refused — the shell names the replay record the
        # boundary minted for this determination (audit by construction).
        assert refusal["replay_reference"].startswith("ccf-artifact://"), verb

    # The reason survives inside the fabric even though it does not cross the
    # wire: dimension 5 of the minted record retains the whole internal
    # determination. Read back through the recorder the door was built with,
    # because a refusal nobody can account for afterwards is exactly what
    # `SEC-002` exists to prevent — and because taking the shell's word for
    # the reason would assert the disclosure rule, not the decision.
    internal = _internal_determination(
        authority_bundle, refusal["replay_reference"]
    )
    assert internal.fields["cause"] == '"unauthorized"'
    assert internal.fields["error_code"] == '"evidence-principal-mismatch"'

    # `product get` is SERVED, and that is what the credential bought. It
    # answered `product-door-ungoverned` while `ccf` had no identity at all;
    # the verified principal is now one this deployment's entitlement policy
    # grants the class and the role, so the door serves it the same bytes it
    # serves any other authorized client. The assertion moved back to `code ==
    # 0` because the posture changed, not because the test was relaxed: the
    # entitlement is declared in `cli_entitlement_source`, and deleting the
    # grant there turns this line red again.
    address = fabric.product_address
    code, out, err = run_cli(
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
    assert code == 0, err
    served = json.loads(out)
    assert served["schema_name"] == address.product_class
    assert served["tenant_id"] == address.tenant
    # The Perspective the door forwarded is DERIVED from the verified grant,
    # never manufactured at the resolver seam (D-IMPL-108): a door that had
    # invented one would be indistinguishable here at the response body, so
    # the value the resolver actually received is what gets asserted.
    forwarded, _request = fabric.resolver_calls[-1]
    assert (forwarded.principal_id, forwarded.role) == (CLI_PRINCIPAL, CLI_ROLE)


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

    # resuming the gate with nothing on the HITL authority path is a typed
    # refusal → exit 1, body printed (SEC-001, security review 2026-09-23).
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
            "approved",
        ],
        capsys,
        dependencies=deps,
    )
    assert code == 1 and "authority path" in out
    # and the execution is where it was: still waiting on its human
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


# --- hitl submit travels the typed authority path --------------------------


def test_hitl_submit_submits_the_typed_action(
    fabric: Fabric,
    deps: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The five-field body of D-IMPL-353 §2 P6: subject, assurance and time
    # are the door's to state (capability, verified claims, injected clock),
    # so the document carries none of them.
    submission = {
        "event_key": "acme-bank/cli-covenant-1/gate",
        "action": "approve",
        "product_content_hash": "0" * 64,
        "annotation": None,
    }
    action_file = tmp_path / "action.yaml"
    action_file.write_text(yaml.safe_dump(submission))
    code, _, _ = run_cli(
        ["hitl", "submit", "--file", str(action_file)],
        capsys,
        dependencies=deps,
    )
    assert code == 0
    recorded = fabric.hitl.submissions(tenant="acme-bank")
    assert submission["event_key"] in {s.event_key for s in recorded}


def test_hitl_submit_output_states_submitted_with_disposition(
    fabric: Fabric,
    deps: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """D-IMPL-62 hardening: the CLI output states ``submitted`` — never
    implies resolution — and carries the honest disposition state."""
    # The five-field body of D-IMPL-353 §2 P6: subject, assurance and time
    # are the door's to state (capability, verified claims, injected clock),
    # so the document carries none of them.
    submission = {
        "event_key": "acme-bank/cli-receipt-1/gate",
        "action": "approve",
        "product_content_hash": "0" * 64,
        "annotation": None,
    }
    action_file = tmp_path / "receipt-action.yaml"
    action_file.write_text(yaml.safe_dump(submission))
    code, out, _ = run_cli(
        ["hitl", "submit", "--file", str(action_file)],
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


# --- hitl submit is the ONLY verb; decide is removed (D-15, Phase 8) --------


def test_hitl_decide_is_absent_from_the_parser(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """D-15: ``ccf hitl decide`` no longer exists — the parser rejects the
    verb as an unknown choice with a nonzero exit; no deprecation path
    remains."""
    from ccf_runtime.cli.main import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["hitl", "decide", "--file", "f"])
    assert excinfo.value.code != 0
    err = capsys.readouterr().err
    assert "invalid choice" in err
    assert "decide" in err

    with pytest.raises(SystemExit):
        parser.parse_args(["hitl", "--help"])
    text = capsys.readouterr().out
    assert "decide" not in text
    assert "deprecated" not in text.lower()


def test_hitl_submit_builds_the_typed_request(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``submit`` — the one verb — builds one RequestSpec, notice-free."""
    from ccf_runtime.cli.main import build_parser

    document = {"event_key": "acme-bank/e/gate", "action": "approve"}
    action_file = tmp_path / "action.yaml"
    action_file.write_text(yaml.safe_dump(document))
    parser = build_parser()

    submit_args = parser.parse_args(["hitl", "submit", "--file", str(action_file)])

    capsys.readouterr()
    submit_specs = submit_args.build(submit_args)
    assert capsys.readouterr().err == ""  # submit is notice-free

    assert len(submit_specs) == 1
    spec = submit_specs[0]
    assert spec.method == "POST"
    assert spec.path == "/hitl/actions"
    assert spec.json == document


def test_hitl_submit_help_states_the_ruled_semantics(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``submit``'s help states the D-IMPL-62 truth."""
    from ccf_runtime.cli.main import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["hitl", "--help"])
    text = " ".join(capsys.readouterr().out.split())  # wrap-tolerant
    assert "submission only" in text
    assert "resolution is the owning primitive's act" in text


# --- skill grant / revoke through the governed ledger ----------------------


def test_skill_grant_and_revoke(
    fabric: Fabric,
    deps: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The two halves of `SEC-012` have met, so this is a plain pass.

    It carried an ``xfail(strict=False)`` while the lanes were apart: the CLI
    had already stopped sending a caller-typed actor, but
    ``GrantRequest.actor`` and ``GrantRevocationRequest.actor`` in
    ``runtime/ccf_runtime/http_api/routes/skill.py`` were still required
    fields on ``extra=forbid`` contracts, so the bodies this CLI builds were
    rejected with 422. That lane has since deleted them and derives the
    principal from the authenticated identity, which is what the marker was
    written to detect — it XPASSed at the join, and a marker kept past the
    condition it describes is a marker that hides the next regression.
    """
    grant = dict(fabric.grants_fixture["grants"]["metrics_tool"])
    grant["agent_definition_hash"] = content_hash(fabric.auto_agent)
    # No `actor` key: the ledger's principal comes from the credential
    # the request carries, never from this document (SEC-012).
    request = {
        "grant": grant,
        "definition_key": fabric.auto_agent_key,
        "definition_version": fabric.auto_agent_version,
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
        ["skill", "revoke", "--grant-hash", grant_hash],
        capsys,
        dependencies=deps,
    )
    assert code == 0

    # revoking a revoked grant is a typed 4xx → exit 1
    code, out, _ = run_cli(
        ["skill", "revoke", "--grant-hash", grant_hash],
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()  # nothing answers here
    # The remote leg is authenticated (SEC-016), so reaching the transport
    # at all now requires a credential — the claim under test is still the
    # transport failure, which is why one is supplied rather than the test
    # being allowed to pass on the credential refusal (a different exit 2).
    monkeypatch.setenv("CCF_TEST_WIRING_TOKEN", "t")
    code, out, err = run_cli(
        [
            "--base-url",
            f"http://127.0.0.1:{port}",
            "--token-env",
            "CCF_TEST_WIRING_TOKEN",
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

    bundle = build_local_dependencies(root=tmp_path, hitl_policy_key=declared_hitl_policy_key(), erasure_trust=declared_erasure_trust())
    # by type, not by intent: --local's bundle IS the object create_app
    # consumes (T-07-27; the Codex shared-abstraction finding)
    assert type(bundle) is ApiDependencies


def test_local_is_suspended_and_names_what_reviving_it_would_cost(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--local` REFUSES, and the refusal names the gap (`SEC-002`).

    This test asserted ``code == 0`` for a `--local` read until Tier 1
    deleted the posture beneath it. `--local` built its app by passing
    ``acknowledge_insecure_default=True``; there is no such arm any more, the
    gate has no arm in which authentication is skipped, and the SDK ships
    exactly one authorizer — ``ControlPlaneTenantAuthorizer``, deny-by-default
    against a scope mapping registered at a pinned version — while
    ``build_local_dependencies`` mints a fresh, EMPTY Control Plane per
    invocation. There is nothing there for that authorizer to decide against.

    The mode therefore fails closed rather than quietly building a weaker
    app, and the refusal is asserted rather than deleted along with the flag:
    what `--local` MEANS under a total gate is an unmade design decision, and
    a suite that tested nothing here would not notice it being answered by
    accident. Exit status 2 on stderr — deployment wiring, the same status a
    missing base URL takes (T-07-26).
    """
    with pytest.raises(SystemExit) as suspended:
        run_cli(
            [
                "--local",
                "--local-root",
                str(tmp_path),
                # SEC-009 (fix round 4, ruling 1): the local bundle takes the
                # deployment's HITL policy key before it can refuse anything.
                "--local-hitl-policy-key",
                "acme-bank/hitl/policy",
                "config",
                "keys",
                "--class-id",
                "ccf.agent-definition",
            ],
            capsys,
        )
    assert suspended.value.code == 2
    err = " ".join(capsys.readouterr().err.split())  # wrap-tolerant
    assert "`--local` is suspended" in err
    # Each of the five seams a local deployment would have to declare, so the
    # message cannot decay into "not supported" without reddening this.
    for seam in (
        "scope mapping",
        "token source",
        "entitlement source",
        "perspective resolver",
        "refusal recorder",
    ):
        assert seam in err, seam
    assert "SEC-002" in err


def test_local_requires_a_root(capsys: pytest.CaptureFixture[str]) -> None:
    """The root is still checked FIRST, before the suspension above.

    Both refusals are exit 2 on stderr, so the status alone cannot tell them
    apart — the message is asserted so this test cannot start passing for the
    other reason (`SEC-002` made that a live possibility rather than a
    hypothetical one).
    """
    with pytest.raises(SystemExit) as refused:
        run_cli(["--local", "config", "keys", "--class-id", "x"], capsys)
    assert refused.value.code == 2
    assert "--local requires --local-root" in capsys.readouterr().err


# --- backends: the adapter names, over the route, with no local path -------


def test_backends_list_reports_every_declared_name(
    deps: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """The route answers about the process hosting it — "what is installed
    here", the first question an adopter asks.

    Driven over the in-process governed app rather than over `--local`, which
    is suspended (`SEC-002`, and the test directly above). The *route* is
    unchanged and is the one any remote client reaches; the only thing that
    moved is which app hosts it, and this one is built with a real authority
    and reached with a real credential.
    """
    from ccf.graph.registry import declared_names

    code, out, _ = run_cli(["backends", "list"], capsys, dependencies=deps)
    assert code == 0
    assert json.loads(out)["backends"] == sorted(declared_names())


def test_backends_with_no_verb_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The noun-verb shape D-IMPL-22 ruled: no bare `ccf backends`."""
    from ccf_runtime.cli.main import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["backends"])
    assert "list" in capsys.readouterr().err


def test_backends_command_holds_no_local_generation_path() -> None:
    """D-IMPL-79: the command travels the route and re-derives nothing.

    Asserted against the source rather than by behaviour, because the
    failure this guards is someone "simplifying" the HTTP hop away — which
    would still pass every behavioural test in this file while costing the
    invariant that the CLI holds no privileged path (T-07-27).
    """
    source = (CLI_SOURCE / "commands" / "backends.py").read_text()
    assert "declared_names" not in source
    assert "RequestSpec" in source


def test_backends_list_surfaces_the_registry_refusal_not_a_traceback(
    deps: Any,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A packaging conflict reaches the operator with the name in it.

    The app runs in-process rather than around the CLI, so the typed 503 the
    route builds travels the same path a remote client sees. It used to run
    under `--local`; that leg is suspended (`SEC-002`), and the injected leg
    that replaced it is in-process the same way — what the test measures is
    the route's own answer, which no part of the gate change touched.
    """
    from ccf.graph.registry import DuplicateBackendName
    from ccf_runtime.http_api.routes import backends as backends_route

    def _conflicted() -> frozenset[str]:
        raise DuplicateBackendName(
            "adapter name 'duplicated' is declared by more than one installed"
            " distribution (acme-adapters, beta-adapters); the fabric does not"
            " choose between them. Run `pip uninstall` on one of them."
        )

    monkeypatch.setattr(backends_route, "declared_names", _conflicted)

    code, out, err = run_cli(["backends", "list"], capsys, dependencies=deps)
    assert code != 0
    assert "acme-adapters" in err and "beta-adapters" in err
    assert "Traceback" not in err and "Traceback" not in out


# --- HTTP-vs-injected equivalence over one real hosted server --------------


def test_injected_and_http_paths_produce_identical_output(
    deps: Any,
    fabric: Fabric,
    authority_bundle: Any,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One bundle, two transports, identical bytes — now THROUGH the gate.

    The equivalence claim is unchanged; the application under it is not.
    ``create_app`` had an ``acknowledge_insecure_default=True`` arm when this
    test was written and the hosted leg used it, so the two legs were
    compared with authentication turned off. That arm is deleted (`SEC-002`),
    and the server below is built with the SAME five-seam authority the
    in-process leg binds, reached with the same credential the CLI resolves
    from a named source. The comparison is strictly stronger than before: it
    now holds through the total gate rather than around it, and a gate that
    answered differently on the two transports would show up right here.
    """
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
        uvicorn.Config(
            create_app(deps, **authority_bundle), log_level="error"
        )
    )
    thread = threading.Thread(
        target=server.run, kwargs={"sockets": [bound]}, daemon=True
    )
    thread.start()
    try:
        while not server.started:
            if not thread.is_alive():
                raise AssertionError("the HTTP server failed to start")
        # The remote leg resolves its credential from a NAMED source
        # (SEC-016), and the value it finds there is the one this suite's
        # token source recognises — the hosted app verifies it for real.
        monkeypatch.setenv("CCF_TEST_EQUIVALENCE_TOKEN", CLI_TOKEN)
        code, http_out, _ = run_cli(
            [
                "--base-url",
                f"http://127.0.0.1:{port}",
                "--token-env",
                "CCF_TEST_EQUIVALENCE_TOKEN",
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
