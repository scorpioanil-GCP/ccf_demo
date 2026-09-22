"""What `examples/cp-22-agent-internal-assembly` sends, and what it refuses to.

All twelve declared gates of `CP-SPEC-022` §G.1 execute here.

THE CENTRAL INVARIANT under test:

    CCF terminates inside Agent B. A2A is an external agent protocol and is
    NOT a CCF delivery surface.

Every assertion is a RELATIONSHIP or an IDENTITY and never an estate count.
**Reads the curated estate through cp-21, seeds nothing** (CLAUDE.md §9).
"""

from __future__ import annotations

import ast
import asyncio
import json
import os
import pathlib
import subprocess
import sys
import time
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
import yaml

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-22-agent-internal-assembly"
CONSUMED = REPO_ROOT / "examples" / "cp-21-large-exposure"

#: CP-22 declares no environment of its own: it consumes cp-21 and reads that
#: rung's variables. That is itself the point — no new binding mechanism.
ESTATE_VARIABLES = (
    "CCF_CP_21_POSTGRES_DSN", "CCF_CP_21_POSTGRES_SCHEMA",
    "CCF_CP_21_FLUREE_URL", "CCF_CP_21_FLUREE_LEDGER",
    "CCF_CP_21_MONGO_URI", "CCF_CP_21_MONGO_DB",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"

DECLARATION: dict[str, Any] = yaml.safe_load(
    (EXAMPLE / "artifacts" / "agent-b.yaml").read_text(encoding="utf-8"))["declaration"]
WIRE: dict[str, Any] = yaml.safe_load(
    (EXAMPLE / "artifacts" / "wire-contract.yaml").read_text(encoding="utf-8"))["declaration"]
QUESTION: dict[str, Any] = yaml.safe_load(
    (EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]

SUBJECT: str = QUESTION["question"]["subject"]
INSTANT: str = QUESTION["question"]["instant"]
UNANSWERABLE: str = QUESTION["unanswerable_subject"]

PORT = 8743
STRICT_PORT = 8744
BINDING = "JSONRPC"


@pytest.fixture(scope="module")
def estate() -> None:
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the cp-22 estate (cp-21's) is not configured: {', '.join(missing)} unset"
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)


def _card_is_up(base_url: str, *, seconds: float = 60.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{base_url}/.well-known/agent-card.json", timeout=2.0).status_code == 200:
                return True
        except Exception:  # noqa: BLE001 — not up yet is expected
            pass
        time.sleep(0.5)
    return False


def _start(port: int, *, strict: bool) -> subprocess.Popen[bytes]:
    command = [sys.executable, str(EXAMPLE / "agent_b.py"), "--port", str(port)]
    if strict:
        command.append("--strict")
    return subprocess.Popen(command)  # noqa: S603


@pytest.fixture(scope="module")
def peer(estate: None) -> Iterator[subprocess.Popen[bytes]]:
    """Agent B, in its OWN OS PROCESS. Nothing here calls its handler."""
    process = _start(PORT, strict=False)
    try:
        assert _card_is_up(f"http://127.0.0.1:{PORT}"), "Agent B did not come up"
        yield process
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            process.kill()


@pytest.fixture(scope="module")
def strict_peer(estate: None) -> Iterator[subprocess.Popen[bytes]]:
    """The same agent at its STRICT tolerance — the only difference."""
    process = _start(STRICT_PORT, strict=True)
    try:
        assert _card_is_up(f"http://127.0.0.1:{STRICT_PORT}"), "strict Agent B did not come up"
        yield process
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            process.kill()


class Exchange:
    """One A2A round trip, with the ACTUAL WIRE BYTES kept."""

    def __init__(self) -> None:
        self.responses: list[bytes] = []
        self.answer: dict[str, Any] | None = None
        self.failure: str | None = None

    @property
    def wire(self) -> bytes:
        return b"".join(self.responses)


def exchange(*, port: int = PORT, subject: str = SUBJECT, instant: str = INSTANT,
             extra: dict[str, Any] | None = None) -> Exchange:
    """Ask over A2A and capture what the socket carried, both ways."""
    from a2a.client import A2ACardResolver, ClientConfig, ClientFactory  # noqa: PLC0415
    from a2a.types import Message, Part, Role, SendMessageRequest  # noqa: PLC0415

    result = Exchange()
    question: dict[str, Any] = {"subject": subject, "instant": instant}
    question.update(extra or {})

    async def go() -> None:
        async def capture(response: httpx.Response) -> None:
            await response.aread()
            result.responses.append(bytes(response.content))

        async with httpx.AsyncClient(timeout=300.0,
                                     event_hooks={"response": [capture]}) as http:
            card = await A2ACardResolver(
                httpx_client=http, base_url=f"http://127.0.0.1:{port}").get_agent_card()
            client = ClientFactory(ClientConfig(
                httpx_client=http, streaming=False,
                supported_protocol_bindings=[BINDING])).create(card)
            try:
                responses = [
                    response async for response in client.send_message(
                        SendMessageRequest(message=Message(
                            message_id="q", role=Role.ROLE_USER,
                            parts=[Part(text=json.dumps(question, sort_keys=True))])))
                ]
            finally:
                await client.close()
            for response in responses:
                if response.WhichOneof("payload") != "message":
                    continue
                text = "".join(part.text for part in response.message.parts if part.text)
                if text:
                    result.answer = json.loads(text)

    try:
        asyncio.run(go())
    except Exception as failure:  # noqa: BLE001 — a peer non-success is an outcome
        result.failure = str(failure)
    return result


def _in_process_answer() -> tuple[dict[str, Any], dict[str, Any]]:
    """Ask the same question in THIS process, through Agent B's own entry.

    `_ask_ccf` carries the guarded import (`AIA-F-07`), so calling it is both
    the honest comparison and the one that cannot pick up another tree's
    `produce`.
    """
    sys.path.insert(0, str(EXAMPLE))
    try:
        import agent_b  # noqa: PLC0415

        payload = agent_b._ask_ccf(subject=SUBJECT, instant=INSTANT, strict=False)
        return dict(payload), dict(agent_b._answer_from(payload))
    finally:
        sys.path.remove(str(EXAMPLE))
        sys.modules.pop("agent_b", None)


@pytest.fixture(scope="module")
def served(peer: subprocess.Popen[bytes]) -> Exchange:
    result = exchange()
    assert result.answer is not None, f"the peer did not answer: {result.failure}"
    return result


# =========================================================================
# AIA-G01 / AIA-G12 — where the assembly happens, and where the wire is
# =========================================================================


def test_agent_b_assembles_in_process_behind_no_door(served: Exchange) -> None:
    """Declared product gate `AIA-G01` (`CP-SPEC-022` §G.1).

    Agent B's only CCF entry is `open_product` in its own process. It opens no
    MCP door, no HTTP door and no subprocess — asserted against the source, so
    a door added later fails here rather than passing quietly.
    """
    source = (EXAMPLE / "agent_b.py").read_text(encoding="utf-8")
    declared = DECLARATION["consumed_product"]
    assert declared["entry"].split(".")[-1] in source
    for door in ("open_door", "build_egress_server", "serve_stdio", "serve_loopback",
                 "create_app", "ProductDoor", "mcp_stdio"):
        assert door not in source, f"Agent B reaches for `{door}`; assembly is in-process"


def test_the_exchange_crosses_a_real_process_boundary(
    peer: subprocess.Popen[bytes], served: Exchange,
) -> None:
    """A DIRECT HANDLER CALL WOULD PROVE THE EXTRACTION AND NOTHING ELSE.

    Declared product gate `AIA-G12` (`CP-SPEC-022` §G.1, ruled 2026-09-21).
    """
    assert peer.pid != os.getpid(), "Agent B is running inside the test process"
    assert peer.poll() is None, "Agent B is not alive"
    # The answer arrived as BYTES OVER A SOCKET, not as a return value.
    assert served.wire, "no wire bytes were captured; nothing crossed a socket"
    assert b"jsonrpc" in served.wire.lower() or b"result" in served.wire


# =========================================================================
# AIA-G02 / AIA-G08 — what the wire may carry INWARD
# =========================================================================


def test_agent_a_contains_no_ccf(estate: None) -> None:
    """THE CONTROL FOR THE WHOLE RUNG.

    Declared product gate `AIA-G02` (`CP-SPEC-022` §G.1). Asserted by AST over
    Agent A's imports and names, not by grepping prose — the docstring
    legitimately explains the claim and would defeat a text scan.
    """
    tree = ast.parse((EXAMPLE / "agent_a.py").read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not [name for name in imported if name.split(".")[0] in ("ccf", "ccf_runtime")], (
        f"Agent A imports CCF: {imported}"
    )
    # And no CCF symbol is referenced anywhere in its code.
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not {name for name in names if name.lower().startswith("ccf")}


def test_only_the_two_admitted_fields_are_read_from_the_wire(estate: None) -> None:
    """Declared product gate `AIA-G02` (`Q3`, ruled 2026-09-21)."""
    admitted = WIRE["inbound_admitted_fields"]
    assert admitted == ["subject", "instant"], admitted
    source = (EXAMPLE / "agent_b.py").read_text(encoding="utf-8")
    # The reader indexes the DECLARED list; it names no field of its own.
    assert "inbound_admitted_fields" in source


def test_a_caller_cannot_steer_the_determination(served: Exchange) -> None:
    """AGENT B EXECUTES AS AGENT B, whatever Agent A claims about itself.

    Declared product gate `AIA-G08` (`Q3`, ruled 2026-09-21). The probe sends
    every field a caller might plausibly use to reach the policy envelope —
    a tolerance, a role, a principal, a regime, a basis, a tenant — and the
    answer must be BYTE-IDENTICAL to the one asked without them.
    """
    probes = {name: "steered" for name in WIRE["inbound_ignored_probes"]}
    probes["debt_tolerance"] = 0.0001
    probes["role"] = "examiner"
    probes["principal_id"] = "PRIN-EX-003"
    steered = exchange(extra=probes)
    assert steered.answer is not None, f"the peer failed under noise: {steered.failure}"
    assert steered.answer == served.answer, (
        "a caller-supplied field changed the determination; the envelope is reachable"
    )


# =========================================================================
# AIA-G03 / AIA-G04 — the answer is the product's answer
# =========================================================================


def test_the_reply_answers_the_question(served: Exchange) -> None:
    """Declared product gate `AIA-G03` (`CP-SPEC-022` §G.1)."""
    answer = served.answer
    assert set(answer) == set(WIRE["outbound_admitted_fields"]), sorted(answer)
    assert QUESTION["expected"]["counterparty"] in answer["answer"]
    assert answer["counterparty"] == QUESTION["expected"]["counterparty"]
    assert answer["as_of"] == INSTANT
    # The RELATIONSHIP, never the figure.
    assert not answer["headroom_usd"].startswith("-")


def test_the_wire_answer_agrees_with_the_in_process_product(served: Exchange) -> None:
    """THE FACT AGREES — and no address is asked to.

    Declared product gate `AIA-G04` (`CP-SPEC-022` §G.1). Ruled 2026-09-21:
    the A2A response is NOT required to preserve CCF content identity, so this
    compares the FACT and never a hash.
    """
    payload, direct = _in_process_answer()
    assert direct["counterparty"] == served.answer["counterparty"]
    assert direct["headroom_usd"] == served.answer["headroom_usd"]


# =========================================================================
# AIA-G05 — the forbidden list, on the ACTUAL WIRE BYTES
# =========================================================================


def test_no_ccf_shaped_structure_crosses_the_wire(served: Exchange) -> None:
    """READ FROM THE SOCKET, not from the response object.

    Declared product gate `AIA-G05` (`CP-SPEC-022` §G.1, ruled 2026-09-21).
    Checking the object before serialization would pass a forbidden value
    carried through a field the object does not name; this reads what the
    socket carried — the agent card included, because that is on the wire too.
    """
    wire = served.wire.decode("utf-8", errors="replace").lower()
    assert wire, "no bytes captured"
    for klass, spec in WIRE["forbidden"].items():
        for token in spec["tokens"]:
            assert token.lower() not in wire, (
                f"the wire carries `{token}` ({klass}): {spec['why']}"
            )


def test_the_extraction_is_lossy_by_a_wide_margin(served: Exchange) -> None:
    """The seam drops most of what it was given, and that is its job.

    Declared product gate `AIA-G05` (`CP-SPEC-022` §C.3 trap 1). The
    RELATIONSHIP is asserted — the answer is a small fraction of the payload —
    never the measured byte counts, which are estate-dependent.
    """
    payload, _ = _in_process_answer()
    assert len(served.answer) < len(payload) / 4, (
        "the answer carries most of the payload's members; nothing was extracted"
    )
    dropped = set(payload) - set(served.answer)
    for member in ("population_debt", "limits", "regime_in_force", "capital_base", "members"):
        assert member in dropped, f"`{member}` survived the extraction"


# =========================================================================
# AIA-G06 / AIA-G07 — a refusal, translated
# =========================================================================


@pytest.fixture(scope="module")
def refused(peer: subprocess.Popen[bytes]) -> Exchange:
    result = exchange(subject=UNANSWERABLE)
    assert result.answer is None, "an unanswerable question returned a business answer"
    return result


def test_a_refusal_carries_no_ccf_vocabulary(refused: Exchange) -> None:
    """G06 IS ABOUT VOCABULARY.

    Declared product gate `AIA-G06` (`CP-SPEC-022` §G.1, ruled 2026-09-21 to
    stay separate from `AIA-G07`).
    """
    wire = refused.wire.decode("utf-8", errors="replace").lower()
    for token in WIRE["forbidden"]["refusal_vocabulary"]["tokens"]:
        assert token.lower() not in wire, f"the refusal leaked `{token}`"
    for klass in ("replay_reference", "context_debt", "policy_and_grant_identifiers"):
        for token in WIRE["forbidden"][klass]["tokens"]:
            assert token.lower() not in wire, f"the refusal leaked `{token}` ({klass})"
    assert WIRE["non_success"]["reason_text"].lower() in (refused.failure or "").lower()


def test_a_refusal_is_never_silently_a_success(refused: Exchange) -> None:
    """G07 IS ABOUT OUTCOME, and a reply could satisfy G06 and fail this.

    Declared product gate `AIA-G07` (`CP-SPEC-022` §G.1).
    """
    assert refused.answer is None, "a refusal arrived as a successful business answer"
    assert refused.failure, "a refusal arrived as neither an answer nor a failure"


# =========================================================================
# AIA-G09 / AIA-G10 / AIA-G11
# =========================================================================


def test_this_tree_imports_no_peering(estate: None) -> None:
    """PEERING IS A DIFFERENT THING and this is not it.

    Declared product gate `AIA-G09` (`CP-SPEC-022` §0.3, ruled 2026-09-21).
    """
    for source in sorted(EXAMPLE.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            names = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                     else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
            for name in names:
                assert "peering" not in name, f"{source.name} imports `{name}`"


def test_debt_governs_without_travelling(
    strict_peer: subprocess.Popen[bytes], served: Exchange,
) -> None:
    """BOTH HALVES.

    Declared product gate `AIA-G10` (`CP-SPEC-022` §G.1, ruled 2026-09-21).
    The SAME question at a tighter declared tolerance yields a DIFFERENT reply
    — so the tolerance reaches the determination — and no debt value appears
    on the wire either way.
    """
    strict = exchange(port=STRICT_PORT)
    assert strict.answer is None, (
        "the strict tolerance served the same answer; the tolerance reaches nothing"
    )
    assert served.answer is not None
    for capture in (served, strict):
        wire = capture.wire.decode("utf-8", errors="replace").lower()
        for token in WIRE["forbidden"]["context_debt"]["tokens"]:
            assert token.lower() not in wire, f"a debt value crossed the wire: `{token}`"


def test_the_decision_is_reconstructible_inside_agent_b(estate: None) -> None:
    """NOTHING OF IT REACHED AGENT A, AND ALL OF IT IS STILL THERE.

    Declared product gate `AIA-G11` (`CP-SPEC-022` §G.1).
    """
    # AGENT B MUST ACTUALLY RESOLVE ITS OWN RECORD. Without this limb the
    # gate would prove that cp-21 writes a record and nothing about Agent B —
    # removing the call from `agent_b.py` would leave it green.
    assert "record_of" in (EXAMPLE / "agent_b.py").read_text(encoding="utf-8"), (
        "Agent B never resolves its replay record; the decision is not reconstructible there"
    )
    # THE TEST USES AGENT B'S OWN GUARDED IMPORT, not a second hand-rolled
    # one. Rolling its own was how this test acquired `AIA-F-07`'s collision
    # for itself after the product was fixed — and a test that reaches the
    # consumed tree by a different route is not testing the route that ships.
    sys.path.insert(0, str(EXAMPLE))
    try:
        import agent_b  # noqa: PLC0415

        from ccf.projection.plan import Perspective  # noqa: PLC0415
        from ccf.replay.record import DecisionReplayRecord  # noqa: PLC0415
        from ccf.replay.serve import ServedProduct  # noqa: PLC0415
        import tempfile  # noqa: PLC0415
        from datetime import datetime  # noqa: PLC0415
        from decimal import Decimal  # noqa: PLC0415

        envelope = DECLARATION["envelope"]
        principal = DECLARATION["principal"]
        with agent_b._consumed_modules() as (produce, deployment):
            with tempfile.TemporaryDirectory() as scratch:
                with produce.product(pathlib.Path(scratch)) as opened:
                    asked = produce.large_exposure_question(
                        opened, anchor=SUBJECT, asked_at=datetime.fromisoformat(INSTANT),
                        intent=envelope["intent"], freshness=envelope["freshness"],
                        **{deployment.AS_OF: INSTANT, deployment.REGIME: envelope["regime"],
                           deployment.CONNECTION_BASIS: envelope["connection_basis"],
                           deployment.APPLY_MITIGATION: envelope["apply_mitigation"],
                           "debt_tolerance": Decimal(str(DECLARATION["debt_tolerance"]))})
                    outcome = opened.answer(asked, perspective=Perspective(
                        principal_id=principal["principal_id"], role=principal["role"]))
                    assert isinstance(outcome, ServedProduct)
                    record = opened.record_of(outcome)
                    assert isinstance(record, DecisionReplayRecord)
                    assert record.content_generation_path.operator_plan
    finally:
        if str(EXAMPLE) in sys.path:
            sys.path.remove(str(EXAMPLE))
        sys.modules.pop("agent_b", None)
