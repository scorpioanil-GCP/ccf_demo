"""CP-14 Gate 2, slice 1 — the five-slot composite on the PAVED ROAD, asked its first real question.

The consumer-side dogfood of `D-IMPL-343`. `examples/cp-14-credit-memo-context`
declares what it requires, who may provide each class, the skills that ask, the
agent that holds the grants, and ONE question mapping; this module opens it
through `produce.product` and asks BGC at the CP-14 instant with the memo's
governed tolerance. The spread producer is REAL and in ANOTHER process —
`examples/cp-03-canonical-obligor-financial-spread/run.py --door`. The other four
producers have no door the paved road can reach (their shipped trees ship no
door, or a stdio door from before `D-IMPL-340`): their declared endpoints are
pointed at a loopback port nothing listens on, so what the SDK reports for them
is its own answer — `producer-unavailable` — and never a manufactured row.

What is held, exactly:

1. At the governed tolerance (0.25) the spread producer WITHHOLDS; the required
   slot is refused; the composite refuses; FIVE child rows are persisted and
   reloaded from a FRESH store instance (`D-IMPL-338`); the retained detail
   names the producer's refusal as its door disclosed it (`tolerance-exceeded`)
   — never `no-producing-skill`, never `ineligible` alone.
2. At tolerance 1.0 — a DIAGNOSTIC that the producer can serve — the spread is
   served and ADMITTED under `provider-controls` with the same content address
   the producer's own proofs hash to; the composite still refuses on the four
   unreachable required slots.
3. The consumer wrote no SDK machinery: the opened product's registry, agent
   and five grants exist because the documents declared them.

**Reads the estate, seeds nothing.**
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactNotFound
from ccf.contracts.canonical import content_hash
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.skills.catalog import SkillCatalog
from ccf.skills.grants import GrantLedger
from tests.examples.test_cp_03_canonical_cross_deployment import DEV_TOKEN, producer

pytestmark = [pytest.mark.postgres]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-14-credit-memo-context"
SPREAD_EXAMPLE = REPO_ROOT / "examples" / "cp-03-canonical-obligor-financial-spread"

CP14_INSTANT = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
BGC = "2549001IGRCG4F0RLD36"
BGC_FACILITY = "FAC-5B8418"
#: The demonstration spread's content address — the producer's own proofs hash
#: to it (dogfood A) and so does the low road (OFC-G23); one product, one address.
DEMONSTRATION_SPREAD_ADDRESS = "122e0a7b0b96565eac64af7cf2fbd0d5238c46529c1914b638b237187cd1c21e"

ESTATE_VARIABLES = ("CCF_CP_14_POSTGRES_DSN", "CCF_CP_14_POSTGRES_SCHEMA", "CCF_CP_03C_POSTGRES_DSN", "CCF_CP_03C_POSTGRES_SCHEMA")
UNREACHABLE = "http://127.0.0.1:1/mcp"
CHILD_CLASSES = (
    "credit-risk.spread",
    "reference.corporate-family",
    "credit-risk.exposure-rollup",
    "credit-risk.collateral-coverage",
    "credit-risk.covenant-cross-reference",
)


@pytest.fixture(scope="module")
def estate() -> None:
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the live estate is not configured: {', '.join(missing)} unset (CLAUDE.md §9)"
        if os.environ.get("CCF_REQUIRE_ESTATE"):
            pytest.fail(message)
        pytest.skip(message)


@pytest.fixture(scope="module")
def modules() -> Iterator[tuple[Any, Any]]:
    """The example's `produce` and `deployment`, imported from its own directory."""
    saved = {name: sys.modules.pop(name, None) for name in ("acquisition", "deployment", "produce", "projection")}
    sys.path.insert(0, str(EXAMPLE))
    try:
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415

        yield produce, deployment
    finally:
        sys.path.remove(str(EXAMPLE))
        for name, module in saved.items():
            sys.modules.pop(name, None)
            if module is not None:
                sys.modules[name] = module


def _environ(spread_url: str) -> dict[str, str]:
    return {
        "CCF_CP_14_POSTGRES_DSN": os.environ["CCF_CP_14_POSTGRES_DSN"],
        "CCF_CP_14_POSTGRES_SCHEMA": os.environ["CCF_CP_14_POSTGRES_SCHEMA"],
        "CCF_CP14_SPREAD_URL": spread_url,
        "CCF_CP14_SPREAD_TOKEN": DEV_TOKEN,
        **{f"CCF_CP14_{name}_URL": UNREACHABLE for name in ("FAMILY", "EXPOSURE", "COLLATERAL", "COVENANT")},
        **{f"CCF_CP14_{name}_TOKEN": "no-door-exists" for name in ("FAMILY", "EXPOSURE", "COLLATERAL", "COVENANT")},
    }


def _ask(modules: tuple[Any, Any], scratch: pathlib.Path, *, spread_url: str, tolerance: str) -> tuple[Any, Any, DecisionReplayRecord]:
    """One question on the paved road; the record reloaded from a FRESH store instance."""
    produce, deployment = modules
    with produce.product(scratch, environ=_environ(spread_url)) as opened:
        asked = opened.question(
            subject=BGC, asked_at=CP14_INSTANT, intent="annual-review", freshness="decision-scoped",
            parameters={
                deployment.AS_OF: CP14_INSTANT.isoformat(),
                deployment.DEBT_TOLERANCE: Decimal(tolerance),
                deployment.FACILITY_ID: BGC_FACILITY,
            },
        )
        outcome = opened.answer(asked)
        fresh = FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)
        if isinstance(outcome, ServedProduct):
            address = outcome.replay_ref.content_address
        else:
            address = fresh.resolve_uri(uri=outcome.replay_reference)
        record = DecisionReplayRecord.model_validate_json(fresh.get(content_address=address))
        return opened, outcome, record


def _rows(record: DecisionReplayRecord) -> dict[str, Any]:
    rows = record.content_generation_path.child_resolutions
    assert [row.required_product_class for row in rows] == list(CHILD_CLASSES), rows
    return {row.required_product_class: row for row in rows}


def test_the_governed_question_refuses_on_the_withheld_spread_with_five_rows_persisted(
    tmp_path: pathlib.Path, modules: tuple[Any, Any], estate: None
) -> None:
    with producer(estate) as url:
        _opened, outcome, record = _ask(modules, tmp_path / "scratch", spread_url=url, tolerance="0.25")
    assert isinstance(outcome, RefusalEnvelope), outcome
    assert outcome.kind == "composite-child-refusal" and outcome.reason == "child_admission"
    rows = _rows(record)
    spread = rows["credit-risk.spread"]
    assert spread.outcome_status == "ineligible" and spread.refusal_ref == "ineligible"
    assert spread.producer_id == "cp-03-canonical-obligor-financial-spread-egress"
    assert spread.producer_tenant == "cp-03-canonical-demo"
    assert spread.producer_server == "canonical-spread-producer"
    assert spread.child_question_address is not None, "the producer was asked"
    assert spread.child_content_address is None
    # D-IMPL-342 / F-05, honestly: no producer replay reference on the refused row.
    assert spread.child_replay_ref is None
    retained = json.loads(record.content_generation_path.assembly_refusal)["detail"]
    assert "tolerance-exceeded" in retained and "no-producing-skill" not in retained, retained
    for product_class in CHILD_CLASSES[1:]:
        row = rows[product_class]
        assert row.outcome_status == "producer-unavailable" and row.child_question_address is not None
        assert row.producer_id is not None and row.producer_tenant is not None
    assert "tolerance-exceeded" not in outcome.detail, "the disclosed envelope stays minimal"


def test_the_diagnostic_tolerance_shows_the_spread_served_and_admitted_at_its_one_address(
    tmp_path: pathlib.Path, modules: tuple[Any, Any], estate: None
) -> None:
    """Tolerance 1.0 is a diagnostic, never the production question: it proves the
    producer CAN serve and the paved road ADMITS it — same bytes, one address —
    while the four unreachable required slots still refuse the composite."""
    with producer(estate) as url:
        opened, outcome, record = _ask(modules, tmp_path / "scratch", spread_url=url, tolerance="1.0")
    assert isinstance(outcome, RefusalEnvelope), outcome
    rows = _rows(record)
    spread = rows["credit-risk.spread"]
    assert spread.outcome_status == "admitted" and spread.eligibility_basis == "provider-controls"
    assert spread.child_content_address == DEMONSTRATION_SPREAD_ADDRESS
    assert spread.child_schema_version == "1.1.0" and spread.child_asked_at == CP14_INSTANT
    assert all(rows[c].outcome_status == "producer-unavailable" for c in CHILD_CLASSES[1:])
    # ON A REFUSED COMPOSITE THE ADMITTED CHILD'S BYTES ARE NOT RETAINED in the
    # consumer's store — only its identity on the row (`CP14-F-32`). Stated,
    # not worked around: a served composite retains them (dogfood B proves it).
    with pytest.raises(ArtifactNotFound):
        FileArtifactStore(root=opened.scratch / opened.replay.store_dirname).get(content_address=spread.child_content_address)


def test_the_consumer_wrote_no_sdk_machinery(tmp_path: pathlib.Path, modules: tuple[Any, Any], estate: None) -> None:
    """The registry, the agent and the five grants exist because the documents
    declared them; the tree constructs none of the low road's objects."""
    produce, _deployment = modules
    with produce.product(tmp_path / "scratch", environ=_environ(UNREACHABLE)) as opened:
        assert opened.mcp_skills is not None and opened.agent is not None
        assert opened.agent.name == "credit-memo-composer"
        assert [c.product_class for c in opened.agent.context_contract.consumes] == list(CHILD_CLASSES)
        ledger = GrantLedger(control_plane=opened.control_plane, catalog=SkillCatalog(opened.control_plane), sink=None, clock=lambda: CP14_INSTANT)  # type: ignore[arg-type]
        bound = ledger.bound_view(content_hash(opened.agent))
        assert sorted(bound) == sorted(f"{name}-ask" for name in ("spread", "family", "exposure", "collateral", "covenant"))
        assert {entry.produces for entry in bound.values()} == set(CHILD_CLASSES)
    forbidden = ("McpSkillRegistry", "register_declared_producer", "SkillCatalog(", "GrantLedger(", "SkillGrant(",
                 "QuestionBoundChildResolver", "CompositeAdmissionGate", "build_governed_resolver", "AgentDefinition(")
    for module in ("produce.py", "deployment.py", "projection.py", "acquisition.py", "run.py"):
        text = (EXAMPLE / module).read_text(encoding="utf-8")
        for name in forbidden:
            assert name not in text, f"{module} constructs {name}"
    for module in sys.modules.values():
        origin = getattr(module, "__file__", None) or ""
        assert not origin.startswith(str(SPREAD_EXAMPLE)), f"the producer's {origin} was imported into the consumer"
