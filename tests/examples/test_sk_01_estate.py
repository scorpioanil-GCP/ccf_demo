# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""sk-01 — declare and govern agent skills: the record and the tool surface, on the live estate (E1–E5).

`examples/sk-01-declare-and-govern-agent-skills` asked its real question: BGC
Group's facility FAC-5B8418 at the CP-14 instant, the collateral child asked of
cp-06-canonical through that producer's own door (``run.py --door``), spawned
here in its own process with a test token. **Reads the estate, seeds nothing** —
and keeps nothing on local disk: the spawned door is started WITHOUT
``CCF_REPLAY_EVIDENCE_ROOT`` (cp-06-canonical's ``serve.py::EVIDENCE_ROOT_VARIABLE``),
so its evidence goes away with its temporary scratch rather than into the
operator's evidence folder. Without the ``CCF_SK_01_*`` and ``CCF_CP_06C_*``
variables every test here SKIPS (or fails under ``CCF_REQUIRE_ESTATE``).

**First run against the estate: 2026-10-16, 5 passed** (read-only). Severing the
agent hand-off in ``src/ccf/products/product.py::_derive_consumer_chain`` turned
E1, E2, E3 and E5 red on their assertions; E4 does not depend on it. The
estate-free O6 (``test_sk_01_offline.py``) holds dimension 4 on a refusal without
the estate; the SDK-level gate is
``tests/products/test_dimension_four_records_the_agent.py``. **A failure while
asking never prints the DSN**: the ``asked`` fixture re-raises it with the
traceback's file and line, the message redacted, and no frame arguments.

Every assertion is a RELATIONSHIP, never an estate count (CLAUDE.md §9):

* **E1** dimension 4 names the declared agent — its content hash, its versioned
  URI, its archetypes — a skill-set that is not the no-grants claim, and the
  caller's own principal and role.
* **E2** the joins: every admitted child row carries a grant; each row that
  carries one names a declared skill, and its hash is the hash the audit log
  recorded as effective at open FOR THAT SKILL (joined by the grant's Control
  Plane key, not by membership); the skill-set in dimension 4 is the set
  identity of those audited grants.
* **E3** on a refusal (the expired-evidence facility), the brief refuses on its
  required child (``composite-child-refusal``), whose row is ``ineligible`` with
  the producer's own ``ttl-refusal`` / ``ttl-bounds`` — the path the README's
  variation names — and the refused record names the DECLARED agent and a
  skill-set that is not the no-grants claim, the same as E1's. The expected path
  comes from the design and cp-06-canonical's own gate (`D-IMPL-341`), not from a
  sk-01 measurement: if it is red on its first live run, that is a finding about
  the expectation, to be classified, never re-pinned.
* **E4** the tool surface: the adapter exposes exactly the bound skills whose type
  has a harness tool surface — none today — and ``allowed_tools`` agrees.
  **A weak gate, stated as such:** it compares two empty tuples, and it cannot
  be severed validly today (FINDINGS.md, SK01-F-01). It becomes meaningful when
  an example can declare a tool-type skill.
* **E5** a second opening on a fresh Control Plane records the DECLARED agent's
  hash, a skill-set that is not the no-grants claim, and the same two hashes as
  the first opening: both are content-addressed.
"""

from __future__ import annotations

import ast
import os
import pathlib
import subprocess
import sys
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

import psycopg
import pytest

from ccf.agents.definitions import AGENT_DEFINITION
from ccf.artifacts.protocol import artifact_uri
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.gates import GATE_TTL_BOUNDS
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.record import CHILD_ADMITTED, NO_GRANTS_SET_HASH
from ccf.skills.grants import SKILL_GRANT, grant_set_hash
from ccf.skills.toolsurface import HARNESS_EXPOSABLE_SKILL_TYPES
from tests.examples.estate_guard import _redacted

pytestmark = [pytest.mark.postgres, pytest.mark.fluree, pytest.mark.harness]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "sk-01-declare-and-govern-agent-skills"
COLLATERAL_RUN = REPO_ROOT / "examples" / "cp-06-canonical-collateral-and-setoff-coverage" / "run.py"
COLLATERAL_SERVE = COLLATERAL_RUN.parent / "server" / "serve.py"
EXAMPLE_MODULES = ("acquisition", "deployment", "produce", "projection", "tool_surface", "run")

#: The token the spawned producer door is started with, and the consumer presents.
TEST_TOKEN = "sk-01-test-token-for-a-loopback-door"

ESTATE_VARIABLES = (
    "CCF_SK_01_POSTGRES_DSN", "CCF_SK_01_POSTGRES_SCHEMA",
    "CCF_CP_06C_FLUREE_URL", "CCF_CP_06C_FLUREE_LEDGER", "CCF_CP_06C_POSTGRES_DSN", "CCF_CP_06C_POSTGRES_SCHEMA",
)

#: The facility whose collateral evidence has expired at the CP-14 instant, and its
#: borrower: cp-06-canonical refuses it, so the brief refuses (E3).
EXPIRED_FACILITY = "FAC-D3D1A4"
EXPIRED_BORROWER = "B3BS7ACMDUWISF18KY76"


@pytest.fixture(scope="module")
def estate() -> None:
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the live estate is not configured: {', '.join(missing)} unset (CLAUDE.md §9)"
        if os.environ.get("CCF_REQUIRE_ESTATE"):
            pytest.fail(message)
        pytest.skip(message)


@pytest.fixture(scope="module")
def modules(estate: None) -> Iterator[tuple[Any, Any, Any]]:
    """The example's ``produce``, ``deployment`` and ``tool_surface``, imported from its own directory."""
    saved = {name: sys.modules.pop(name, None) for name in EXAMPLE_MODULES}
    sys.path.insert(0, str(EXAMPLE))
    try:
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415
        import tool_surface  # noqa: PLC0415

        yield produce, deployment, tool_surface
    finally:
        sys.path.remove(str(EXAMPLE))
        for name, original in saved.items():
            sys.modules.pop(name, None)
            if original is not None:
                sys.modules[name] = original


def _door_evidence_variable() -> str:
    """cp-06-canonical's ``serve.py::EVIDENCE_ROOT_VARIABLE``, read from its source — never imported, never restated."""
    for node in ast.parse(COLLATERAL_SERVE.read_text(encoding="utf-8")).body:
        if (
            isinstance(node, ast.Assign)
            and [getattr(target, "id", None) for target in node.targets] == ["EVIDENCE_ROOT_VARIABLE"]
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    raise AssertionError(f"{COLLATERAL_SERVE} no longer assigns EVIDENCE_ROOT_VARIABLE; re-read SK01-SEC-02")


@contextmanager
def collateral_producer() -> Iterator[str]:
    """cp-06-canonical's own paved door, ``run.py --door``, in its own process.

    Started WITHOUT the door's evidence-root variable, so a test run leaves no
    question it asked in the operator's evidence folder.
    """
    evidence = _door_evidence_variable()
    env = {key: value for key, value in os.environ.items() if key != evidence} | {"CCF_CP_06C_DOOR_TOKEN": TEST_TOKEN}
    process = subprocess.Popen(
        [sys.executable, str(COLLATERAL_RUN), "--door"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
    )
    try:
        assert process.stdout is not None
        announcement = process.stdout.readline().strip()
        if not announcement.startswith("READY "):
            _, stderr = process.communicate(timeout=10)
            raise AssertionError(f"the collateral door did not announce readiness ({announcement!r}); stderr:\n{_redacted(stderr[-2000:])}")
        yield f"http://127.0.0.1:{int(announcement.split()[1])}/mcp"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def _environ(url: str) -> dict[str, str]:
    return {
        "CCF_SK_01_POSTGRES_DSN": os.environ["CCF_SK_01_POSTGRES_DSN"],
        "CCF_SK_01_POSTGRES_SCHEMA": os.environ["CCF_SK_01_POSTGRES_SCHEMA"],
        "CCF_SK_01_COLLATERAL_URL": url,
        "CCF_SK_01_COLLATERAL_TOKEN": TEST_TOKEN,
    }


def _ask(opened: Any, deployment: Any, *, subject: str, facility: str) -> Any:
    question = deployment.QUESTION
    return opened.answer(opened.question(
        subject=subject,
        asked_at=datetime.fromisoformat(str(question["demonstration"]["asked_at"])),
        intent=str(question["brief"]["intent"]),
        freshness=str(question["brief"]["freshness"]),
        parameters={str(question["brief"]["facility_parameter"]): facility},
    ))


@pytest.fixture(scope="module")
def asked(modules: tuple[Any, Any, Any], tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Both questions, and a second opening, with the producer door live — asked once per module."""
    produce, deployment, tool_surface = modules
    scratch = tmp_path_factory.mktemp("sk01")
    demonstration = deployment.QUESTION["demonstration"]
    results: dict[str, Any] = {"server": str(tool_surface.harness()["mcp_server_name"])}
    try:
        with collateral_producer() as url:
            environ = _environ(url)
            registry = ControlPlaneRegistry()
            with produce.product(scratch / "first", control_plane=registry, environ=environ) as opened:
                outcome = _ask(opened, deployment, subject=str(demonstration["subject"]), facility=str(demonstration["facility"]))
                refused = _ask(opened, deployment, subject=EXPIRED_BORROWER, facility=EXPIRED_FACILITY)
                results["first"] = {
                    "opened": opened, "registry": registry,
                    "record": opened.record_of(outcome), "refused": refused, "refused_record": opened.record_of(refused),
                    "surface": tool_surface.tool_surface(opened, instant=datetime.fromisoformat(str(demonstration["asked_at"]))),
                    "agent": opened.agent, "default_perspective": opened.default_perspective,
                    "grants": tuple(opened.config.grants), "tenant": opened.tenant_id,
                }
            second = ControlPlaneRegistry()
            with produce.product(scratch / "second", control_plane=second, environ=environ) as opened:
                outcome = _ask(opened, deployment, subject=str(demonstration["subject"]), facility=str(demonstration["facility"]))
                results["second"] = {"record": opened.record_of(outcome)}
    except Exception as exc:  # noqa: BLE001 - a CREDENTIAL decision (tests/conftest.py): the frames below hold the DSN as an argument
        # `from None` drops the chained psycopg exception, whose message for a
        # malformed URI is the whole DSN; `pytrace=False` drops the frames and
        # their arguments; `format_tb` keeps file, line and source, never locals.
        said = (
            "(message withheld: a conninfo parse error echoes the DSN)"
            if isinstance(exc, psycopg.ProgrammingError)
            else _redacted(str(exc))
        )
        where = "".join(traceback.format_tb(exc.__traceback__))
        raise pytest.fail.Exception(f"asking failed: {type(exc).__name__}: {said}\n{where}", pytrace=False) from None
    return results


def _effective(registry: ControlPlaneRegistry) -> dict[str, str]:
    """The grant hash audited ``grant_effective``, by the grant's Control Plane key."""
    return {event.key: event.version for event in registry.audit_log.events() if event.action == "grant_effective"}


def test_e1_dimension_four_names_the_declared_agent_and_a_skill_set(asked: dict[str, Any]) -> None:
    first = asked["first"]
    agent = first["agent"]
    d4 = first["record"].perspective_conditioning
    assert d4.agent_definition_hash == content_hash(agent)
    assert d4.agent_definition_uri == artifact_uri(
        tenant_id=first["tenant"], artifact_class=AGENT_DEFINITION.class_id, name=agent.name, artifact_version=agent.artifact_version,
    )
    assert tuple(d4.archetype_composition) == tuple(agent.archetypes)
    assert d4.grant_set_hash != NO_GRANTS_SET_HASH
    caller = first["default_perspective"]
    assert (d4.principal_id, d4.role) == (caller.principal_id, caller.role)


def test_e2_the_child_row_and_dimension_four_join_to_the_audit_log(asked: dict[str, Any]) -> None:
    first = asked["first"]
    effective = _effective(first["registry"])
    assert effective, "no grant was put in force at open"
    d4 = first["record"].perspective_conditioning
    assert d4.grant_set_hash == grant_set_hash(frozenset(effective.values()))
    rows = first["record"].content_generation_path.child_resolutions
    assert all(row.grant_hash is not None for row in rows if row.outcome_status == CHILD_ADMITTED), (
        "an admitted child row carries no grant", [(row.outcome_status, row.grant_hash) for row in rows],
    )
    granted = [row for row in rows if row.grant_hash is not None]
    assert granted, f"no child row carries a grant: {[row.outcome_status for row in rows]}"
    for row in granted:
        assert row.producing_skill_name in first["grants"]
        # Joined by the row's OWN skill, under the grant's Control Plane key — not by membership.
        key = f"{first['tenant']}/{SKILL_GRANT.class_id}/{row.producing_skill_name}"
        assert effective.get(key) == row.grant_hash, (key, row.grant_hash)
    assert grant_set_hash(frozenset(row.grant_hash for row in granted)) == d4.grant_set_hash


#: Where E3's expected refusal path comes from: not a sk-01 measurement.
E3_BASIS = (
    "expected from the sk-01 design and cp-06-canonical's own gate on this facility (D-IMPL-341,"
    " test_cp_06_canonical_output.py), not measured by sk-01; red on a first live run is a finding"
    " to classify (docs/EXAMPLE-EVALUATION-CRITERIA.md), never a value to re-pin"
)


def test_e3_a_refused_decision_names_the_same_agent_and_skill_set(asked: dict[str, Any], modules: tuple[Any, Any, Any]) -> None:
    first = asked["first"]
    _, deployment, _ = modules
    refusal = first["refused"]
    assert isinstance(refusal, RefusalEnvelope), refusal
    assert refusal.kind == "composite-child-refusal", (refusal.kind, refusal.reason, E3_BASIS)
    rows = [
        row for row in first["refused_record"].content_generation_path.child_resolutions
        if row.required_product_class == deployment.CHILD_CLASS
    ]
    assert len(rows) == 1, ([row.required_product_class for row in rows], E3_BASIS)
    (row,) = rows
    assert row.outcome_status == "ineligible", (row.outcome_status, E3_BASIS)
    assert row.producer_refusal_kind == "ttl-refusal", (row.producer_refusal_kind, E3_BASIS)
    assert row.producer_refusal_reason == GATE_TTL_BOUNDS, (row.producer_refusal_reason, E3_BASIS)
    served = first["record"].perspective_conditioning
    refused = first["refused_record"].perspective_conditioning
    # Anchored to the DECLARED agent first: two records that both lost the agent
    # would otherwise agree ('no-agent' == 'no-agent').
    assert refused.agent_definition_hash == content_hash(first["agent"])
    assert refused.grant_set_hash != NO_GRANTS_SET_HASH
    assert (refused.agent_definition_hash, refused.grant_set_hash) == (served.agent_definition_hash, served.grant_set_hash)


def test_e4_the_tool_surface_is_exactly_the_bound_harness_exposable_skills(asked: dict[str, Any]) -> None:
    """A weak gate today (``() == ()``); see the module docstring and SK01-F-01."""
    first = asked["first"]
    surface = first["surface"]
    assert tuple(surface.bound) == first["grants"]
    expected = tuple(sorted(name for name, kind in surface.bound.items() if kind in HARNESS_EXPOSABLE_SKILL_TYPES))
    assert surface.exposed == expected
    server = asked["server"]
    assert set(surface.allowed_tools) == {f"mcp__{server}__{name}" for name in expected}
    assert surface.definition_hash == content_hash(first["agent"])


def test_e5_a_second_opening_records_the_same_agent_and_skill_set(asked: dict[str, Any]) -> None:
    first = asked["first"]["record"].perspective_conditioning
    second = asked["second"]["record"].perspective_conditioning
    # Anchored to the DECLARED agent first, so a total loss of identity cannot pass as equality.
    assert first.agent_definition_hash == content_hash(asked["first"]["agent"])
    assert first.grant_set_hash != NO_GRANTS_SET_HASH
    assert (second.agent_definition_hash, second.grant_set_hash) == (first.agent_definition_hash, first.grant_set_hash)
