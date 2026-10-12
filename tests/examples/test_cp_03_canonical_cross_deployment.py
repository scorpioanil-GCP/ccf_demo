# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""`CP14-F-22` §6 — the canonical spread acquired across a deployment boundary.

A composite in THIS process requires `credit-risk.spread`; the canonical
producer (`examples/cp-03-canonical-obligor-financial-spread/server/serve.py`,
booted by `run.py --door`) runs in ANOTHER process, booted under its own tenant and reached only through
the SDK's authenticated egress door with the `request_context_product` tool
exposed. The consumer holds a `ccf.mcp-producer` registration, an
`mcp_product` grant, a `QuestionBoundChildResolver` and the admission gate —
and nothing of the producer's.

The question is the one `CP-SPEC-014` will ask: `subject` = one of its roster
LEIs, `asked_at` = the instant it is held to (`CP14-F-19`), `intent` and
`freshness` the spread class serves, and the spread's own parameters.

**This is not CP-14 Gate 2.** The parent here is the SDK's fixture composite,
not a credit-memo product; what is proved is that a real, governed
`credit-risk.spread` child can be acquired through `D-IMPL-340` and admitted.

**AMENDED 2026-10-11, round 4 (`examples/AMENDMENTS-2026-10-11.md`).** This
module used to compose the consumer BY HAND (the "low road"): it registered a
policy regime, a catalog entry and a grant on the Control Plane itself and
built the question-bound resolver directly. Since `D-IMPL-353` every one of
those writes needs a capability only SDK composition mints — the regime
registration is refused `CapabilityBypassError`, a grant needs
`Authorized[SkillGrant]`, and the question-bound resolver needs
`Authorized[ReplayMint]` at construction — and a test that minted them would be
inventing the grant (Dave, 2026-10-11: "Do not obtain success by bypassing a
gate or inventing a grant"). The consumer is therefore composed on the ONE
supported path: the DECLARED consumer document
`cp_03_canonical_paved_consumer/ccf_config.yaml` (`requires`, `producers:`,
`skills:`, `agent:`, `grants:`) opened through `open_product`, whose
composition requests the declared grant through the ledger's own governance.
The variants each gate needs (another expected producer identity or tenant,
another lane floor, another tolerance) are edits to that declaration, made in
memory. Every gate's assertion is unchanged except where the paved road
answers at a different boundary by design; each such case says so in place.
`test_the_hand_composed_low_road_is_closed` keeps the reason executable.

**Reads the estate, seeds nothing.** The producer process reads the same live
estate the in-process example reads; this module reads none of it directly.
"""

from __future__ import annotations

import copy
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator, Mapping
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
import yaml

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import CapabilityBypassError
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import MCP_PRODUCER, declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.erasure import ErasureTrust
from ccf.products.child_resolver import ChildQuestion
from ccf.products.contract import ChildRequirement, ContextProductContract
from ccf.products.product import OpenedProduct, open_product
from ccf.products.request import ProductRequest
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from tests.deployment.conftest import write_artifact
from tests.products import paved_fixture as fixture
from tests.products.paved_fixture import THRESHOLD_PARAMETER

pytestmark = [pytest.mark.postgres]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-03-canonical-obligor-financial-spread"
RUN = EXAMPLE / "run.py"

#: The producer's OWN declarations, read from its tree rather than restated:
#: the identity its door asserts and the tenant its fabric runs as — both from
#: the ONE document the paved road declares them in (`D-IMPL-343`). A consumer
#: registers what the producer declares; equality is a binding, never an
#: authorization.
CONFIG = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
PRODUCER_ID = str(CONFIG["door"]["producer_id"])
PRODUCER_TENANT = str(CONFIG["tenant_id"])
PRODUCT_CLASS = str(CONFIG["product_class"]["schema_name"])
PRODUCT_VERSION = str(CONFIG["product_class"]["schema_version"])
INTENT = sorted(CONFIG["product_class"]["discovery"]["intents"])[0]
FRESHNESS = "filing-cadence"

#: The consumer's DECLARED document — the one supported composition (round 4).
CONSUMER = pathlib.Path(__file__).resolve().parent / "cp_03_canonical_paved_consumer"
CONSUMER_CONFIG: dict[str, Any] = yaml.safe_load((CONSUMER / "ccf_config.yaml").read_text(encoding="utf-8"))
TENANT = str(CONSUMER_CONFIG["tenant_id"])

#: The consumer's logical name for the producer — what its `McpProductBinding`
#: selects by. The consumer's vocabulary, not the producer's.
SERVER_NAME = "canonical-spread-producer"
SKILL = "spread-ask"
ENDPOINT_VAR = "CCF_TEST_CP03C_PRODUCER_URL"
CREDENTIAL_VAR = "CCF_TEST_CP03C_PRODUCER_TOKEN"
DEV_TOKEN = "dev-token-cp-03-canonical-door"
CALL_TIMEOUT_SECONDS = 120.0

#: The instant CP-14 asks at (`CP14-F-19`), and the clock a child admission is
#: judged against — seven minutes on, as the SDK's own fixture pins it.
CP14_INSTANT = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
ADMITTED_AT = CP14_INSTANT + timedelta(minutes=7)

#: A `CP-SPEC-014` §C.1 roster obligor whose latest filing lies inside the
#: spread's declared window at the CP-14 instant (BGC Group), and one that does
#: not (Digital Turbine — not on the roster; the specimen's own anchor).
ROSTER_OBLIGOR = "2549001IGRCG4F0RLD36"
STALE_OBLIGOR = "549300D0WZR1VI2QGB24"

ESTATE_VARIABLES = ("CCF_CP_03C_POSTGRES_DSN", "CCF_CP_03C_POSTGRES_SCHEMA")


@pytest.fixture(scope="module")
def estate() -> None:
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the live estate is not configured: {', '.join(missing)} unset (CLAUDE.md §9)"
        if os.environ.get("CCF_REQUIRE_ESTATE"):
            pytest.fail(message)
        pytest.skip(message)


@dataclass
class _Consumer:
    """Every consuming deployment one test opens, under one owned tmp root.

    Round 4: the consumer is the DECLARED one, opened through `open_product`;
    this holder keeps the opened products open until the test ends.
    """

    root: pathlib.Path
    stack: ExitStack = field(default_factory=ExitStack)
    opened: list[OpenedProduct] = field(default_factory=list)


@pytest.fixture
def booted(tmp_path: pathlib.Path) -> Iterator[_Consumer]:
    """The consumer side: the fixture composite REQUIRING `credit-risk.spread`."""
    holder = _Consumer(root=tmp_path / "consumers")
    holder.root.mkdir()
    with holder.stack:
        yield holder


@contextmanager
def producer(estate: None, **environment: str) -> Iterator[str]:
    """The producer process — the example's own door, spawned via `run.py --door`.

    Readiness is a handshake: the child prints `READY {port}` once the server
    is up. The parent learns the bearer credential by SETTING it, through the
    one variable the door names; no side channel.
    """
    env = {**os.environ, "CCF_CP_03C_DOOR_TOKEN": DEV_TOKEN, **environment}
    process = subprocess.Popen(
        [sys.executable, str(RUN), "--door"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
    )
    try:
        assert process.stdout is not None
        announcement = process.stdout.readline().strip()
        if not announcement.startswith("READY "):
            _, stderr = process.communicate(timeout=10)
            raise AssertionError(f"the door did not announce readiness (got {announcement!r}); stderr:\n{stderr[-2000:]}")
        yield f"http://127.0.0.1:{int(announcement.split()[1])}/mcp"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


class _Recording:
    """Every URL this process requests over `httpx`, and every client it opens.

    Round 4: the declared consumer builds its own MCP client, so the recording
    is an instrument on `httpx.AsyncClient` for the life of the consumer rather
    than a credential factory handed to a hand-built registration. It observes;
    it changes nothing the client sends.
    """

    def __init__(self) -> None:
        self.urls: list[str] = []
        self.sessions = 0

    @contextmanager
    def watching(self) -> Iterator[_Recording]:
        original_init = httpx.AsyncClient.__init__
        original_send = httpx.AsyncClient.send
        recording = self

        def init(client: httpx.AsyncClient, *args: Any, **kwargs: Any) -> None:
            recording.sessions += 1
            original_init(client, *args, **kwargs)

        async def send(client: httpx.AsyncClient, request: httpx.Request, *args: Any, **kwargs: Any) -> Any:
            recording.urls.append(str(request.url))
            return await original_send(client, request, *args, **kwargs)

        httpx.AsyncClient.__init__ = init  # type: ignore[method-assign]
        httpx.AsyncClient.send = send  # type: ignore[method-assign]
        try:
            yield self
        finally:
            httpx.AsyncClient.__init__ = original_init  # type: ignore[method-assign]
            httpx.AsyncClient.send = original_send  # type: ignore[method-assign]


def producer_document(
    *, producer_id: str = PRODUCER_ID, producer_tenant: str = PRODUCER_TENANT,
    offered_class: str = PRODUCT_CLASS, versions_from: str = PRODUCT_VERSION,
) -> dict[str, Any]:
    """A `ccf.mcp-producer` document — names only, never an address."""
    return {
        "semver": "1.0.0",
        "server": SERVER_NAME,
        "producer_id": producer_id,
        "producer_tenant": producer_tenant,
        "endpoint_from_env": ENDPOINT_VAR,
        "credential_from_env": CREDENTIAL_VAR,
        "offers": [{"product_class": offered_class, "versions_from": versions_from}],
    }


def questions_at(tolerance: str) -> Callable[[ChildRequirement, ProductRequest], ChildQuestion]:
    """The consumer's mapping — the CP-14-shaped question for the spread slot.

    The composite's subject (an obligor LEI) reaches the child as ITS subject;
    the intent and freshness are the ones the spread class serves; the
    parameters are the spread's own, with numbers as decimal TEXT. `asked_at`
    is not here: it is the composite's instant, supplied by dispatch.
    """

    def questions(requirement: ChildRequirement, request: ProductRequest) -> ChildQuestion:
        return ChildQuestion(
            subject=request.subject,
            intent=INTENT,
            freshness=FRESHNESS,
            parameters={"debt_tolerance": tolerance},
        )

    return questions


def consumer(
    booted: _Consumer, *, url: str, recording: _Recording | None = None,
    document: Mapping[str, Any] | None = None, tolerance: str = "1.0", requires_from: str | None = None,
) -> tuple[OpenedProduct, _Recording]:
    """The consuming deployment, DECLARED: registration → grant → resolver, all derived.

    ``document`` replaces the declared producer registration (the consumer's
    expectation of the producer — the only thing the identity gates vary);
    ``requires_from`` replaces the parent's lane floor.
    """
    config = copy.deepcopy(CONSUMER_CONFIG)
    if document is not None:
        declared = {key: value for key, value in document.items() if key != "semver"}
        config["producers"]["spread"] = declared
    if requires_from is not None:
        config["product_class"]["requires"][0]["compatible_from"] = requires_from
    root = pathlib.Path(tempfile.mkdtemp(prefix="consumer-", dir=booted.root))  # owned: under the test's tmp_path
    (root / "config").mkdir()
    write_artifact(root / "config", "ccf_config.yaml", config)
    (root / "config" / "ccf_environment.yaml").write_text(
        (CONSUMER / "ccf_environment.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    watched = booted.stack.enter_context((recording or _Recording()).watching())
    opened = booted.stack.enter_context(
        open_product(
            erasure_trust=ErasureTrust(authorities={}),
            control_plane=ControlPlaneRegistry(),
            config_root=root / "config",
            scratch=root / "scratch",
            acquire=fixture.Acquire(),
            project=fixture.plan_factory,
            assess=fixture.assess,
            questions=questions_at(tolerance),
            environ={ENDPOINT_VAR: url, CREDENTIAL_VAR: DEV_TOKEN},
            clock=lambda: ADMITTED_AT,
        )
    )
    booted.opened.append(opened)
    return opened, watched


def ask(opened: OpenedProduct, *, subject: str = ROSTER_OBLIGOR) -> Any:
    outcome = opened.answer(
        opened.question(
            subject=subject, asked_at=CP14_INSTANT, intent="fixture-intent",
            freshness="fixture-freshness", parameters={THRESHOLD_PARAMETER: 1000},
        )
    )
    _ANSWERED[id(outcome)] = (outcome, opened)
    return outcome


#: Which opened consumer answered which outcome (kept alive with it).
_ANSWERED: dict[int, tuple[Any, OpenedProduct]] = {}


def record_of(booted: _Consumer, outcome: Any) -> DecisionReplayRecord:
    return _ANSWERED[id(outcome)][1].record_of(outcome)


def the_row(booted: _Consumer, outcome: Any) -> Any:
    rows = record_of(booted, outcome).content_generation_path.child_resolutions
    assert len(rows) == 1, rows
    return rows[0]


def store_root(opened: OpenedProduct) -> pathlib.Path:
    return opened.scratch / opened.replay.store_dirname


def reader(root: pathlib.Path) -> FileArtifactStore:
    """A READ-ONLY view of a consumer's store: it declares no mechanism-written
    class, so any write through it would need a client capability nobody here
    holds (`D-IMPL-353` §1.2)."""
    return FileArtifactStore(root=root, write_kinds=WriteKinds.declare({}))


def retained_child(booted: _Consumer, address: str) -> ContextProductContract:
    for opened in booted.opened:
        store = reader(store_root(opened))
        try:
            return ContextProductContract.model_validate_json(store.get(content_address=address))
        except Exception:  # noqa: BLE001 — not retained by THIS consumer; try the next
            continue
    raise AssertionError(f"no consumer of this test retained {address}")


# --- the proof ------------------------------------------------------------------


def test_the_cp14_question_is_answered_by_the_producer_in_another_process_and_admitted(
    booted: _Consumer, estate: None
) -> None:
    """A CP-14-shaped question → `mcp_product` → the canonical producer, in
    another process → a governed `credit-risk.spread` child → admission. The
    row records `provider-controls`, the registered producer, the producer's
    tenant, the child's class, and the question's address; the retained child
    is the spread for the subject asked, at the instant asked, on the lane the
    requirement admits.

    Declared product gate `OFC-G16` (`CP-SPEC-003C` §G.1).
    """
    with producer(estate) as url:
        resolver, recording = consumer(booted, url=url)
        served = ask(resolver)
    assert isinstance(served, ServedProduct), getattr(served, "detail", served)
    row = the_row(booted, served)
    assert row.outcome_status == "admitted"
    assert row.eligibility_basis == "provider-controls"
    assert row.producing_fabric == PRODUCER_ID
    assert row.producer_id == PRODUCER_ID
    assert row.producer_tenant == PRODUCER_TENANT
    assert row.producer_server == SERVER_NAME
    assert row.producer_registration_address == content_hash(parse_artifact(producer_document(), MCP_PRODUCER))
    assert row.child_schema_name == PRODUCT_CLASS
    assert row.child_question_address is not None
    child = retained_child(booted, row.child_content_address)
    assert child.schema_name == PRODUCT_CLASS
    assert child.schema_version == PRODUCT_VERSION
    assert child.tenant_id == PRODUCER_TENANT
    assert child.temporal_boundary == CP14_INSTANT
    assert child.payload["obligor"]["lei"] == ROSTER_OBLIGOR
    assert child.ttl_anchor == "from_entity_freshness"
    assert recording.sessions == 1
    assert all(u.startswith(url) for u in recording.urls), recording.urls


def test_the_consumer_process_runs_no_producer_assembler(
    booted: _Consumer, estate: None
) -> None:
    """After a real acquisition: the producer's modules are not imported here,
    no spread fabric exists under this deployment's root, the producer's replay
    record is not in this store, and the child's replay reference is the
    producer's own — unresolvable here.

    Declared product gate `OFC-G17` (`CP-SPEC-003C` §G.1).
    """
    with producer(estate) as url:
        resolver, _ = consumer(booted, url=url)
        served = ask(resolver)
    assert isinstance(served, ServedProduct), getattr(served, "detail", served)
    for module in sys.modules.values():
        origin = getattr(module, "__file__", None) or ""
        assert not origin.startswith(str(EXAMPLE)), f"the producer's {origin} was imported into the consumer"
    assert not list(booted.root.rglob("cp_03_canonical*.sqlite3"))
    index = json.loads((store_root(resolver) / ".artifact-names.json").read_text())
    assert [key for key in index if key.startswith(f"{PRODUCER_TENANT}/")] == []
    row = the_row(booted, served)
    assert row.child_replay_ref is not None
    assert row.child_replay_ref.startswith(f"ccf-artifact://{PRODUCER_TENANT}/")
    with pytest.raises(Exception):
        reader(store_root(resolver)).resolve_uri(uri=row.child_replay_ref)


def test_the_expected_producer_identity_and_tenant_come_from_the_registration(
    booted: _Consumer, estate: None
) -> None:
    """The same door, the same bytes: only the consumer's registration changes.
    Expecting another producer id refuses `producer-mismatch`; expecting another
    tenant refuses `producer-tenant-mismatch`. Neither is authorized by the
    door's own claim about itself.

    Declared product gate `OFC-G18` (`CP-SPEC-003C` §G.1).
    """
    with producer(estate) as url:
        impostor, _ = consumer(booted, url=url, document=producer_document(producer_id="somebody-else-egress"))
        refused_id = ask(impostor)
        moved, _ = consumer(booted, url=url, document=producer_document(producer_tenant="some-other-tenant"))
        refused_tenant = ask(moved)
    assert not isinstance(refused_id, ServedProduct)
    row = the_row(booted, refused_id)
    assert row.refusal_ref == "producer-mismatch"
    assert row.producer_id == "somebody-else-egress"  # what was EXPECTED
    assert not isinstance(refused_tenant, ServedProduct)
    row = the_row(booted, refused_tenant)
    assert row.refusal_ref == "producer-tenant-mismatch"
    assert row.producer_tenant == "some-other-tenant"
    assert row.child_content_address is None


def test_a_lane_the_requirement_does_not_admit_is_refused_and_an_unoffered_class_is_an_error(
    booted: _Consumer, estate: None
) -> None:
    """Class and version are still established on the producer leg: a parent
    requiring a lane above the served `1.1.0` refuses the child
    `version-incompatible`; a registration offering a lane the requirement can
    never admit never opens a socket — a wiring error, not a governed refusal.

    Declared product gate `OFC-G19` (`CP-SPEC-003C` §G.1).

    AMENDED 2026-10-11 round 4: on the declared road the two floors are checked
    against each other when the consumer OPENS (`D-IMPL-343` R-13), so the cases
    split by major. Within the major (requirement floor `1.2.0`, producer floor
    `1.1.0`) the door serves `1.1.0` and the ADMISSION gate refuses it
    `version-incompatible` — this gate's governed refusal, unchanged. Across
    majors (requirement `2.0.0`; or an offer from `3.0.0`) the open refuses by
    name before any socket exists, where the hand-composed consumer used to
    reach `version-incompatible` at admission or `ProducerDoesNotOffer` at the
    ask: the same verdict, at the earlier boundary the declared road has.
    """
    with producer(estate) as url:
        resolver, recording = consumer(booted, url=url, requires_from="1.2.0")
        refused = ask(resolver)
        assert not isinstance(refused, ServedProduct)
        row = the_row(booted, refused)
        assert row.refusal_ref == "version-incompatible"
        assert row.outcome_status == "rejected-at-admission"
        assert recording.urls and all(u.startswith(url) for u in recording.urls), recording.urls
    with pytest.raises(ValueError, match="R-13"):
        consumer(booted, url="http://127.0.0.1:1/mcp", requires_from="2.0.0")
    with pytest.raises(ValueError, match="R-13"):
        consumer(booted, url="http://127.0.0.1:1/mcp", document=producer_document(versions_from="3.0.0"))


def test_no_question_argument_becomes_an_address_and_the_childs_own_gate_governs(
    booted: _Consumer, estate: None
) -> None:
    """A subject shaped like a URL reaches the producer as a subject string and
    the only host this process contacted is the registered endpoint. The
    producer resolves no such obligor and refuses on its OWN declared gate; the
    consumer records the child refusal and refuses the composite on its
    required slot — no fake spread child.

    Declared product gate `OFC-G20` (`CP-SPEC-003C` §G.1).
    """
    # AMENDED 2026-10-11 round 4: since `D-IMPL-357` C1 the SDK's subject floor
    # (`SUBJECT_FLOOR_V1`, an address grammar with no `?`) refuses the original
    # hostile subject at the PARENT, before any child question exists — a
    # stronger outcome, asserted here first. The producer-leg half of the gate
    # is then exercised with the floor-admissible URL-shaped subject.
    with producer(estate) as url:
        floored, floor_recording = consumer(booted, url=url)
        at_the_floor = ask(floored, subject="http://evil.invalid/steal?x=1")
        assert not isinstance(at_the_floor, ServedProduct)
        assert (at_the_floor.reason, at_the_floor.key) == ("malformed-value", "subject"), at_the_floor
        assert floor_recording.urls == [], "a subject refused at the parent's floor reached the network"
    hostile = "http://evil.invalid/steal"
    with producer(estate) as url:
        resolver, recording = consumer(booted, url=url)
        refused = ask(resolver, subject=hostile)
    assert recording.urls and all(u.startswith(url) for u in recording.urls), recording.urls
    assert not any("evil.invalid" in u for u in recording.urls)
    assert not isinstance(refused, ServedProduct)
    assert refused.reason == "child_admission"
    row = the_row(booted, refused)
    assert row.outcome_status == "ineligible" and row.refusal_ref == "ineligible"
    assert row.child_content_address is None
    assert row.child_question_address is not None
    assert row.producer_id == PRODUCER_ID


def test_at_cp14s_own_tolerance_the_spread_slot_is_withheld_and_the_composite_refuses(
    booted: _Consumer, estate: None
) -> None:
    """Estate truth, preserved across the boundary. At `CP-SPEC-014`'s own
    tolerance the producer withholds the spread with the debt block; the
    consumer records that child outcome and refuses the composite on its
    required slot. The number was not moved to fit the ceiling.

    Declared product gate `OFC-G21` (`CP-SPEC-003C` §G.1).
    """
    with producer(estate) as url:
        resolver, _ = consumer(booted, url=url, tolerance="0.25")
        refused = ask(resolver)
    assert not isinstance(refused, ServedProduct)
    assert refused.reason == "child_admission"
    row = the_row(booted, refused)
    # The producer's refusal reaches the consumer as an `ineligible` row whose
    # producer claims were held first; the producer's own reason and record
    # stay on the producer's side (`CP03C-F-05`).
    assert row.outcome_status == "ineligible" and row.refusal_ref == "ineligible"
    assert row.child_content_address is None
    assert row.producer_id == PRODUCER_ID and row.producer_tenant == PRODUCER_TENANT


def test_a_severed_producer_is_a_governed_refusal_not_a_fake_child(
    booted: _Consumer, estate: None
) -> None:
    """A correctly registered producer at a port nothing listens on: the slot is
    `producer-unavailable`, the composite refuses with the row, a record
    exists, and no exception crosses the composition.

    Declared product gate `OFC-G22` (`CP-SPEC-003C` §G.1).
    """
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        dead_port = probe.getsockname()[1]
    resolver, _ = consumer(booted, url=f"http://127.0.0.1:{dead_port}/mcp")
    refused = ask(resolver)
    assert not isinstance(refused, ServedProduct)
    row = the_row(booted, refused)
    assert row.outcome_status == "producer-unavailable"
    assert row.refusal_ref == "producer-unavailable"
    assert row.child_content_address is None


def test_the_door_and_the_in_process_run_serve_one_content_address(
    booted: _Consumer, estate: None
) -> None:
    """The product is the constant; the transport is the variable. The child
    retained through the door hashes to the address the same question hashes
    to when the example is run in this process — same bytes, two doors.

    Declared product gate `OFC-G23` (`CP-SPEC-003C` §G.1).
    """

    with producer(estate) as url:
        resolver, _ = consumer(booted, url=url)
        served = ask(resolver)
    assert isinstance(served, ServedProduct), getattr(served, "detail", served)
    through_the_door = the_row(booted, served).child_content_address

    saved = {name: sys.modules.pop(name, None) for name in ("acquisition", "assembler", "deployment", "produce", "projection")}
    sys.path.insert(0, str(EXAMPLE))
    try:
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as scratch, produce.product(pathlib.Path(scratch)) as opened:
            asked = opened.question(
                subject=ROSTER_OBLIGOR, asked_at=CP14_INSTANT, intent=INTENT, freshness=FRESHNESS,
                parameters={deployment.DEBT_TOLERANCE: "1.0"},
            )
            local = opened.answer(asked)
        assert isinstance(local, ServedProduct), getattr(local, "detail", local)
        assert content_hash(local.product) == through_the_door
    finally:
        sys.path.remove(str(EXAMPLE))
        for name, module in saved.items():
            sys.modules.pop(name, None)
            if module is not None:
                sys.modules[name] = module


def test_the_hand_composed_low_road_is_closed() -> None:
    """Why this module composes its consumer from the declaration (round 4).

    The first write the hand-composed consumer made — registering its own
    policy regime on its own Control Plane — is refused without a capability,
    and nothing in this module can supply one without minting it (`D-IMPL-353`
    §1.1, §1.6). The declared road is the supported path, not a convenience.
    """
    registry = ControlPlaneRegistry()
    regime_class = declared_artifact_class("policy-bundle")
    regime = parse_artifact(
        {
            "class_id": "policy-bundle",
            "semver": "1.0.0",
            "declaration": {
                "regime": "cp-03-canonical-consumer",
                "skill_governance": {"grant_requires_approval": False, "permitted_scopes": []},
            },
        },
        regime_class,
    )
    with pytest.raises(CapabilityBypassError):
        registry.register_typed(f"{TENANT}/policy-bundle/cp-03-canonical", regime, regime_class)  # type: ignore[call-arg]
