"""The ``ccf`` CLI authenticates its remote leg, and never types the actor.

Written before the implementation per the TDD discipline. Two security
findings are asserted here.

**SEC-016 — the CLI could not authenticate.** Before this module the
shipped CLI held zero ``Authorization``/``Bearer`` references in any of
its 15 source files (measured by grep over
``runtime/ccf_runtime/cli/``), so an operator handed an authenticated
HTTP API had no way to reach it and the only working configuration was
one with authentication turned off. The claims below are that a remote
invocation carries a bearer credential, that the credential is resolved
from a *named* source the deployment supplies (D-08's discipline — a
name travels, a value does not), that no value is accepted on the
command line, that no value is ever echoed, and — the load-bearing one —
that a remote invocation with **no** credential configured **refuses**
rather than proceeding anonymously. A guard the caller can decide not to
be subject to is not a guard; the SDK therefore offers no opt-out, and
the WR-02/WR-03 lesson recorded in
:func:`ccf.deployment.manifest._resolve_secret_references` — "a
credentialed URL connected anonymously ... the failure was silent" — is
the precedent this follows.

**SEC-012 — the caller typed the audit actor.** ``skill revoke --actor``
(and the ``actor:`` key in a ``skill grant`` request file) let whoever
ran the command name the principal written into the replay-relevant
grant ledger. The claims below are that the flag no longer exists, that
the request body the CLI builds carries no actor, and that a grant file
naming one is refused rather than silently stripped — silently stripping
would leave the operator believing they had set something.

**SEC-002 — the exemption is gone.** This module recorded one boundary:
"the local leg is unchanged", on the reasoning that ``--local`` hosts no
network boundary and so resolves no credential. That reasoning does not
survive a TOTAL gate. ``--local`` is suspended, and the in-process leg
that replaced it is gated like any other — the claim below is that an
in-process invocation without a bearer is refused, and that no value of
the ``authority`` parameter builds an application that would have let it
through.

**Exit codes.** Unchanged and still true (see
:mod:`ccf_runtime.cli.main`): a missing or unusable credential is
deployment *wiring*, reported on stderr with status 2, exactly as a
missing base URL already was. A grant file that names an actor is a verb
refusing its own inputs — a typed refusal, status 1 on stdout. A
credential the door does not recognise is that door's typed refusal,
status 1 on stdout, since it crossed the boundary and was answered.
"""

from __future__ import annotations

import json
import socket
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
import yaml

from cli.conftest import run_cli

#: A token value that exists only in this module. Nothing in the SDK ships
#: a token (CINV-01), so the tests mint their own — and the disclosure
#: test below greps every stream for this exact string.
TOKEN = "cli-test-token-6f2a9c"

#: The variable name a deployment would point ``--token-env`` at. A name,
#: never a value: the SDK has no default variable, because a default
#: location for a secret is a place an attacker knows to look
#: (:class:`ccf_runtime.mcp.auth.FileTokenSource`, same reasoning).
TOKEN_VAR = "CCF_TEST_CLI_TOKEN"


@contextmanager
def recording_server() -> Iterator[tuple[int, list[str | None]]]:
    """A loopback server recording the ``Authorization`` header it saw.

    Deliberately not the fabric's own app: the claim under test is what
    the CLI *puts on the wire*, and the cheapest honest witness to that
    is a socket that writes down what arrived.
    """
    seen: list[str | None] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            seen.append(self.headers.get("Authorization"))
            body = b"[]"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            return  # the test output is not a web server log

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1], seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)


@pytest.fixture(autouse=True)
def no_ambient_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test in this module inherits a credential from the operator."""
    for name in ("CCF_TOKEN_ENV", "CCF_TOKEN_FILE", "CCF_BASE_URL", TOKEN_VAR):
        monkeypatch.delenv(name, raising=False)


def _dead_port() -> int:
    """A port nothing answers on — for the refusal-before-request claims."""
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port: int = probe.getsockname()[1]
    probe.close()
    return port


# --- SEC-016: the remote leg carries a credential --------------------------


def test_remote_invocation_sends_a_bearer_credential(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The header the SDK could not previously produce reaches the wire."""
    monkeypatch.setenv(TOKEN_VAR, TOKEN)
    with recording_server() as (port, seen):
        code, _, _ = run_cli(
            [
                "--base-url",
                f"http://127.0.0.1:{port}",
                "--token-env",
                TOKEN_VAR,
                "skill",
                "list",
            ],
            capsys,
        )
    assert code == 0
    assert seen == [f"Bearer {TOKEN}"]


def test_a_token_file_is_read_and_sent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file source works too — it is what makes a token revocable."""
    token_file = tmp_path / "token"
    token_file.write_text(f"{TOKEN}\n", encoding="utf-8")
    with recording_server() as (port, seen):
        code, _, _ = run_cli(
            [
                "--base-url",
                f"http://127.0.0.1:{port}",
                "--token-file",
                str(token_file),
                "skill",
                "list",
            ],
            capsys,
        )
    assert code == 0
    # trailing newline is file formatting, not credential material
    assert seen == [f"Bearer {TOKEN}"]


def test_the_credential_source_may_come_from_the_environment(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``CCF_TOKEN_ENV`` configures it without a flag, as the base URL does."""
    monkeypatch.setenv(TOKEN_VAR, TOKEN)
    monkeypatch.setenv("CCF_TOKEN_ENV", TOKEN_VAR)
    with recording_server() as (port, seen):
        code, _, _ = run_cli(
            ["--base-url", f"http://127.0.0.1:{port}", "skill", "list"],
            capsys,
        )
    assert code == 0
    assert seen == [f"Bearer {TOKEN}"]


# --- SEC-016: no credential is a refusal, never an anonymous call ----------


def test_a_remote_call_without_a_credential_refuses(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The defect this finding names: proceeding unauthenticated.

    Exit 2 on stderr — deployment wiring, the sibling of a missing base
    URL — and *no request is attempted*, which the dead port witnesses:
    a request would have produced a transport error, not a usage error.
    """
    with pytest.raises(SystemExit) as exited:
        run_cli(
            ["--base-url", f"http://127.0.0.1:{_dead_port()}", "skill", "list"],
            capsys,
        )
    assert exited.value.code == 2
    err = capsys.readouterr().err
    assert "--token-env" in err and "--token-file" in err


def test_there_is_no_flag_that_disables_the_credential(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No opt-out exists: applicability is not the caller's to decide."""
    from ccf_runtime.cli.main import build_parser

    parser = build_parser()
    for flag in ("--no-auth", "--insecure", "--anonymous", "--no-token"):
        with pytest.raises(SystemExit):
            parser.parse_args([flag, "skill", "list"])


def test_a_named_variable_that_is_unset_refuses(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Naming a source asserts a credential is required (D-08 precedent)."""
    with pytest.raises(SystemExit) as exited:
        run_cli(
            [
                "--base-url",
                f"http://127.0.0.1:{_dead_port()}",
                "--token-env",
                TOKEN_VAR,
                "skill",
                "list",
            ],
            capsys,
        )
    assert exited.value.code == 2
    assert TOKEN_VAR in capsys.readouterr().err  # the NAME is nameable


def test_a_named_variable_that_is_empty_refuses(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Empty is not "no credential"; it is a misconfiguration."""
    monkeypatch.setenv(TOKEN_VAR, "   ")
    with pytest.raises(SystemExit) as exited:
        run_cli(
            [
                "--base-url",
                f"http://127.0.0.1:{_dead_port()}",
                "--token-env",
                TOKEN_VAR,
                "skill",
                "list",
            ],
            capsys,
        )
    assert exited.value.code == 2


def test_a_missing_token_file_refuses(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exited:
        run_cli(
            [
                "--base-url",
                f"http://127.0.0.1:{_dead_port()}",
                "--token-file",
                str(tmp_path / "absent"),
                "skill",
                "list",
            ],
            capsys,
        )
    assert exited.value.code == 2


def test_an_empty_token_file_refuses(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty = tmp_path / "token"
    empty.write_text("\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exited:
        run_cli(
            [
                "--base-url",
                f"http://127.0.0.1:{_dead_port()}",
                "--token-file",
                str(empty),
                "skill",
                "list",
            ],
            capsys,
        )
    assert exited.value.code == 2


def test_two_credential_sources_at_once_refuses(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Which credential was in force is an audit fact; it cannot be guessed."""
    monkeypatch.setenv(TOKEN_VAR, TOKEN)
    token_file = tmp_path / "token"
    token_file.write_text(TOKEN, encoding="utf-8")
    with pytest.raises(SystemExit) as exited:
        run_cli(
            [
                "--base-url",
                f"http://127.0.0.1:{_dead_port()}",
                "--token-env",
                TOKEN_VAR,
                "--token-file",
                str(token_file),
                "skill",
                "list",
            ],
            capsys,
        )
    assert exited.value.code == 2


# --- SEC-016: the value never travels in argv, and never into output -------


def test_no_flag_takes_a_token_value() -> None:
    """A secret in ``argv`` is a secret in ``ps``; no such flag exists."""
    from ccf_runtime.cli.main import build_parser

    parser = build_parser()
    for flag in ("--token", "--bearer", "--auth-token", "--password"):
        with pytest.raises(SystemExit):
            parser.parse_args([flag, TOKEN, "skill", "list"])


def test_the_token_value_is_never_echoed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A wiring error reports the failure, never the credential."""
    monkeypatch.setenv(TOKEN_VAR, TOKEN)
    code, out, err = run_cli(
        [
            "--base-url",
            f"http://127.0.0.1:{_dead_port()}",
            "--token-env",
            TOKEN_VAR,
            "skill",
            "list",
        ],
        capsys,
    )
    assert code == 2
    assert TOKEN not in out and TOKEN not in err


def test_the_resolved_credential_masks_itself() -> None:
    """Held as ``SecretStr``: an accidental interpolation prints a mask."""
    from ccf_runtime.cli.credential import resolve_remote_credential

    credential = resolve_remote_credential(
        token_env=TOKEN_VAR,
        token_file=None,
        environ={TOKEN_VAR: TOKEN},
    )
    assert TOKEN not in repr(credential) and TOKEN not in str(credential)
    assert credential.get_secret_value() == TOKEN


def test_the_sdk_names_no_default_credential_source() -> None:
    """No default variable and no default path — both are deployment values.

    A default location for a secret is a place an attacker knows to look
    (the reasoning :class:`ccf_runtime.mcp.auth.FileTokenSource` already
    records), and a default here would also make "which credential was in
    force" unanswerable. Both knobs therefore default to nothing, and
    nothing is a refusal rather than an anonymous call.
    """
    from ccf_runtime.cli.credential import (
        CredentialUnresolved,
        resolve_remote_credential,
    )
    from ccf_runtime.cli.main import build_parser

    parsed = build_parser().parse_args(["skill", "list"])
    assert parsed.token_env is None and parsed.token_file is None
    with pytest.raises(CredentialUnresolved):
        resolve_remote_credential(token_env=None, token_file=None, environ={})


# --- the in-process leg is a request like any other (SEC-002) --------------


def test_the_in_process_leg_requires_a_credential_too(
    deps: Any, authority_bundle: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """The absence of a network boundary entitles nothing (`SEC-002`).

    This asserted the opposite — that ``--local`` "hosts no network leg, so
    it resolves no credential" — and Tier 1 deleted the posture that made it
    true. ``--local`` is suspended outright, and the in-process leg that
    replaced it drives an app built with the same five seams as any other: a
    pure-ASGI middleware gates EVERY request before any handler exists. So an
    in-process request carrying no bearer is refused exactly as a remote one
    is, and the exemption this test used to record no longer exists anywhere
    in the CLI.

    Both arms are measured, because a refusal with no positive control beside
    it is indistinguishable from a leg that never worked: the same command,
    same bundle and same authority answers `0` with the recognised credential
    and `1` without one.

    Driven through ``main`` rather than through ``run_cli``, since ``run_cli``
    supplies the credential for the rest of the suite — a test of what happens
    without one has to be the thing that withholds it.
    """
    from pydantic import SecretStr

    from ccf_runtime.cli.main import main

    from cli.conftest import CLI_TOKEN

    refused = main(
        ["skill", "list"],
        dependencies=deps,
        authority=authority_bundle,
        credential=None,
    )
    anonymous = capsys.readouterr()
    # A typed refusal: status 1 with the body on stdout, the same contract a
    # 4xx over HTTP takes (T-07-26). Nothing of the catalog crossed.
    assert refused == 1
    assert json.loads(anonymous.out)["detail"]["error_code"] == (
        "unauthenticated"
    )
    assert anonymous.err == ""

    served = main(
        ["skill", "list"],
        dependencies=deps,
        authority=authority_bundle,
        credential=SecretStr(CLI_TOKEN),
    )
    assert served == 0
    assert json.loads(capsys.readouterr().out)


def test_no_value_of_authority_builds_an_unauthenticated_app(
    deps: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Omitting the authority REFUSES; it does not fall back (`SEC-002`).

    A guard whose applicability the caller decides is not a guard. There is
    no ``authority=None`` arm that builds a permissive application for an
    embedder or a test — the invocation exits 2 on stderr as deployment
    wiring, which is the same answer ``--local`` gets for the same reason:
    nothing has declared what this app would be allowed to do.
    """
    from pydantic import SecretStr

    from ccf_runtime.cli.main import main

    from cli.conftest import CLI_TOKEN

    with pytest.raises(SystemExit) as wiring:
        main(
            ["skill", "list"],
            dependencies=deps,
            authority=None,
            credential=SecretStr(CLI_TOKEN),
        )
    assert wiring.value.code == 2
    assert capsys.readouterr().out == ""


# --- SEC-012: the audit actor is not the caller's to type ------------------


def test_skill_revoke_has_no_actor_flag() -> None:
    from ccf_runtime.cli.main import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["skill", "revoke", "--grant-hash", "h", "--actor", "whoever"]
        )


def test_skill_revoke_body_carries_no_actor() -> None:
    """The replay-relevant ledger entry gets its principal from elsewhere."""
    from ccf_runtime.cli.main import build_parser

    args = build_parser().parse_args(
        ["skill", "revoke", "--grant-hash", "h"]
    )
    (spec,) = args.build(args)
    assert spec.json == {"grant_hash": "h"}


def test_skill_grant_refuses_a_caller_typed_actor(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Refused, not silently stripped: a strip leaves a false belief."""
    request_file = tmp_path / "grant.yaml"
    request_file.write_text(
        yaml.safe_dump(
            {
                "grant": {},
                "definition_key": "k",
                "definition_version": "1.0.0",
                "actor": "whoever",
            }
        )
    )
    code, out, _ = run_cli(
        ["skill", "grant", "--file", str(request_file)], capsys
    )
    assert code == 1  # a verb refusing its own inputs, per the contract
    assert "actor" in out


def test_skill_grant_body_carries_no_actor(tmp_path: Path) -> None:
    from ccf_runtime.cli.main import build_parser

    request_file = tmp_path / "grant.yaml"
    request_file.write_text(
        yaml.safe_dump(
            {"grant": {}, "definition_key": "k", "definition_version": "1.0.0"}
        )
    )
    args = build_parser().parse_args(
        ["skill", "grant", "--file", str(request_file)]
    )
    (spec,) = args.build(args)
    assert isinstance(spec.json, dict)
    assert "actor" not in spec.json
