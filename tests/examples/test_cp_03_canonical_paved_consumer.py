"""`D-IMPL-343` dogfood B — the cross-deployment proof's CONSUMER side on the paved road.

The producer is unchanged: `examples/cp-03-canonical-obligor-financial-spread`,
booted by `run.py --door` in ANOTHER process, reached only through the SDK's
authenticated egress door. What changes is how the consumer is written. The
low road (`test_cp_03_canonical_cross_deployment.py`) builds the consumer by
hand: a skill registry, a producer registration, a regime, an agent
definition, a catalog entry, a grant, an admission gate, a question-bound
resolver and a fifteen-keyword resolver — ≈ 100 lines of Python. The paved
road writes four declarations (`requires`, `producers:`, `skills:`, `agent:`)
in `cp_03_canonical_paved_consumer/ccf_config.yaml`, one `remote` setting in
its environment document, and ONE Python mapping — the question — and opens.

**Functional equivalence is the proof, not a claim.** Every test that admits a
child here also runs the low road's own `consumer()` against the same producer
process and compares the CHILD-LEVEL identities row by row: the child's
content address (same bytes, two consumers), the producer identity, the
producer tenant, the registration address (the same document, so the same
hash), the question identity, the admission basis, the admitted child's class,
lane, tenant, instant and obligor, and the producer's replay reference. What
legitimately differs is named in the same test: the parent's own pins and the
grant's identity, because the two parents are two deployments.

**`R-13` against the real producer.** The spread is served at lane `1.1.0`. A
consumer declaring floor `1.0.0` at both boundaries is served (the door accepts
a floor its lane satisfies); a consumer declaring floor `2.0.0` is refused at
the producer's door with the reason retained through to the consumer's record
— `class-mismatch` at `schema_version` — and never `no-producing-skill`. The
low road reaches its verdict for the same mismatch at ADMISSION
(`version-incompatible`, `OFC-G19`), because it addresses the exact lane; both
refuse, both retain the reason, and the boundary differs by design.

**Reads the estate, seeds nothing.** The producer process reads the live
estate; this module reads none of it directly.
"""

from __future__ import annotations

import copy
import json
import pathlib
import sys
from collections.abc import Callable, Iterator
from typing import Any

import pytest
import yaml

from ccf.erasure import ErasureTrust
from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import MCP_PRODUCER, parse_artifact
from ccf.products.child_resolver import ChildQuestion
from ccf.products.contract import ChildRequirement, ContextProductContract
from ccf.products.product import OpenedProduct, open_product
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.replay.serve import ServedProduct
from tests.deployment.conftest import write_artifact
from tests.examples.test_cp_03_canonical_cross_deployment import (
    ADMITTED_AT,
    CP14_INSTANT,
    CREDENTIAL_VAR,
    DEV_TOKEN,
    ENDPOINT_VAR,
    EXAMPLE,
    FRESHNESS,
    INTENT,
    PRODUCER_ID,
    PRODUCER_TENANT,
    PRODUCT_CLASS,
    PRODUCT_VERSION,
    ROSTER_OBLIGOR,
    SERVER_NAME,
    SKILL,
    _Booted,
    ask,
    booted,  # noqa: F401  # the low road's fixture, imported so the equivalence leg can boot it
    bridge,  # noqa: F401
    consumer,
    estate,  # noqa: F401
    producer,
    producer_document,
    the_row,
)
from tests.products import paved_fixture as fixture
from tests.products.paved_fixture import THRESHOLD_PARAMETER
from ccf.controlplane.registry import ControlPlaneRegistry

pytestmark = [pytest.mark.postgres]

CONSUMER = pathlib.Path(__file__).resolve().parent / "cp_03_canonical_paved_consumer"
CONFIG: dict[str, Any] = yaml.safe_load((CONSUMER / "ccf_config.yaml").read_text(encoding="utf-8"))

#: The row members that MUST agree between the two consumers — the child's
#: identity and the producer relationship — and the ones that legitimately
#: differ because the two parents are two deployments.
CHILD_IDENTITY = (
    "outcome_status", "eligibility_basis", "child_content_address", "child_schema_name", "child_schema_version",
    "child_asked_at", "child_graph_snapshot_at", "child_debt", "child_lineage_ref", "child_operators_invoked",
    "child_expires_at", "child_policy_bundle_versions", "producer_id", "producer_tenant", "producer_server",
    "producer_registration_address", "child_question_address", "child_replay_ref", "producing_skill_name",
    "producing_skill_version", "required_product_class", "required", "producing_fabric",
    "child_eligibility_checked_at", "child_eligibility_assertion_address",
    # `D-IMPL-342`: the producer's own refusal, as its door disclosed it — the
    # producer's word, so it must agree between two consumers (both None here:
    # the spread was admitted).
    "producer_refusal_kind", "producer_refusal_reason", "producer_refusal_key",
    # `D-IMPL-341`: the child's declared anchor and the instant it ran from, as
    # the producer's own contract states them — child identity, so they must
    # agree between two consumers of the same child.
    "child_ttl_anchor", "child_ttl_anchor_at",
)
# `child_question_ref` (`D-IMPL-342` / `CP14-F-35`): each parent retains the
# question on ITS OWN store under its own tenant, so the reference differs while
# the address it resolves to (`child_question_address`, above) agrees.
PARENT_OWNED = ("grant_hash", "child_admitted_at", "child_reported_address", "child_debt_factors", "refusal_ref", "child_question_ref")


def questions_at(tolerance: str) -> Callable[[ChildRequirement, ProductRequest], ChildQuestion]:
    """The consumer's ONE mapping — identical in content to the low road's `questions_at`."""

    def questions(requirement: ChildRequirement, request: ProductRequest) -> ChildQuestion:
        return ChildQuestion(subject=request.subject, intent=INTENT, freshness=FRESHNESS, parameters={"debt_tolerance": tolerance})

    return questions


def _tree(tmp_path: pathlib.Path, *, edit: Callable[[dict[str, Any]], None] | None = None) -> pathlib.Path:
    """The checked-in consumer documents, optionally edited in memory for a control."""
    config = copy.deepcopy(CONFIG)
    if edit is not None:
        edit(config)
    root = tmp_path / "consumer"
    root.mkdir(parents=True)
    write_artifact(root, "ccf_config.yaml", config)
    (root / "ccf_environment.yaml").write_text((CONSUMER / "ccf_environment.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    return root


def paved(tmp_path: pathlib.Path, *, url: str, tolerance: str = "1.0", edit: Callable[[dict[str, Any]], None] | None = None) -> OpenedProduct:
    """The consuming deployment on the paved road: four declarations, one mapping, one call."""
    return open_product(
        erasure_trust=ErasureTrust(authorities={}),
        control_plane=ControlPlaneRegistry(),
        config_root=_tree(tmp_path, edit=edit),
        scratch=tmp_path / "scratch",
        acquire=fixture.Acquire(),
        project=fixture.plan_factory,
        assess=fixture.assess,
        questions=questions_at(tolerance),
        environ={ENDPOINT_VAR: url, CREDENTIAL_VAR: DEV_TOKEN},
        clock=lambda: ADMITTED_AT,
    )


def ask_paved(opened: OpenedProduct, *, subject: str = ROSTER_OBLIGOR) -> Any:
    return opened.answer(
        opened.question(subject=subject, asked_at=CP14_INSTANT, intent="fixture-intent", freshness="fixture-freshness", parameters={THRESHOLD_PARAMETER: 1000})
    )


def paved_row(opened: OpenedProduct, outcome: Any) -> Any:
    rows = opened.record_of(outcome).content_generation_path.child_resolutions
    assert len(rows) == 1, rows
    return rows[0]


def paved_child(opened: OpenedProduct, address: str) -> ContextProductContract:
    return ContextProductContract.model_validate_json(
        FileArtifactStore(root=opened.scratch / opened.replay.store_dirname).get(content_address=address)
    )


# --- the proof ------------------------------------------------------------------


def test_the_paved_consumer_admits_the_spread_with_the_low_roads_child_identities(
    tmp_path: pathlib.Path, booted: _Booted, bridge: Any, estate: None
) -> None:
    """One producer process, two consumers: the low road and the paved road
    admit the SAME child — every child-level row member equal, the retained
    child byte-identical — and the parent-owned members are the ones that differ.
    `OFC-G16`'s consumer side, re-expressed.
    """
    with producer(estate) as url:
        low_resolver, _ = consumer(booted, url=url, bridge=bridge)
        low = ask(low_resolver)
        with paved(tmp_path, url=url) as opened:
            served = ask_paved(opened)
            assert isinstance(served, ServedProduct), getattr(served, "detail", served)
            row = paved_row(opened, served)
            child = paved_child(opened, row.child_content_address)
    assert isinstance(low, ServedProduct), getattr(low, "detail", low)
    low_row = the_row(booted, low)
    assert row.outcome_status == "admitted" and row.eligibility_basis == "provider-controls"
    differing = {name for name in CHILD_IDENTITY if getattr(row, name) != getattr(low_row, name)}
    assert differing == set(), {name: (getattr(row, name), getattr(low_row, name)) for name in differing}
    assert row.grant_hash != low_row.grant_hash, "two parents, two grants — named, not hidden"
    assert set(row.model_fields) == set(CHILD_IDENTITY) | set(PARENT_OWNED), "every row member is classified"
    # The same bytes: the child retained by both consumers hashes to one address.
    assert content_hash(child) == row.child_content_address == low_row.child_content_address
    assert (child.schema_name, child.schema_version, child.tenant_id) == (PRODUCT_CLASS, PRODUCT_VERSION, PRODUCER_TENANT)
    assert child.temporal_boundary == CP14_INSTANT and child.payload["obligor"]["lei"] == ROSTER_OBLIGOR
    assert child.ttl_anchor == "from_entity_freshness"
    # The registration the paved road derived from `producers.spread` IS the
    # low road's hand-built document: same content, same address.
    assert row.producer_registration_address == content_hash(parse_artifact(producer_document(), MCP_PRODUCER))
    assert (row.producer_id, row.producer_tenant, row.producer_server, row.producing_skill_name) == (PRODUCER_ID, PRODUCER_TENANT, SERVER_NAME, SKILL)


def test_the_paved_consumer_runs_no_producer_assembler_and_holds_no_producer_record(
    tmp_path: pathlib.Path, estate: None
) -> None:
    """`OFC-G17`'s consumer side: the producer's modules are not imported, no
    spread fabric exists under the consumer's scratch, the producer's records
    are not in the consumer's store, and the child's replay reference is the
    producer's own — unresolvable here."""
    with producer(estate) as url, paved(tmp_path, url=url) as opened:
        served = ask_paved(opened)
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        row = paved_row(opened, served)
        store_root = opened.scratch / opened.replay.store_dirname
    for module in sys.modules.values():
        origin = getattr(module, "__file__", None) or ""
        assert not origin.startswith(str(EXAMPLE)), f"the producer's {origin} was imported into the consumer"
    assert not list((tmp_path / "scratch").rglob("cp_03_canonical*.sqlite3"))
    index = json.loads((store_root / ".artifact-names.json").read_text())
    assert [key for key in index if key.startswith(f"{PRODUCER_TENANT}/")] == []
    assert row.child_replay_ref is not None and row.child_replay_ref.startswith(f"ccf-artifact://{PRODUCER_TENANT}/")
    with pytest.raises(Exception):
        FileArtifactStore(root=store_root).resolve_uri(uri=row.child_replay_ref)


def test_r13_a_floor_the_served_lane_satisfies_serves_and_one_it_does_not_is_refused_with_the_reason(
    tmp_path: pathlib.Path, estate: None
) -> None:
    """The spread is served at `1.1.0`. Floor `1.0.0` at both boundaries: served,
    admitted, the child at its served lane. Floor `2.0.0` at both: the door
    refuses `class-mismatch` at `schema_version`, the composite refuses on its
    required slot with the reason retained in its record — not
    `no-producing-skill`, not a retry, not a downgrade. `OFC-G19`, paved."""

    def floors(value: str) -> Callable[[dict[str, Any]], None]:
        def edit(config: dict[str, Any]) -> None:
            config["product_class"]["requires"][0]["compatible_from"] = value
            config["producers"]["spread"]["offers"][0]["versions_from"] = value

        return edit

    with producer(estate) as url:
        with paved(tmp_path / "below", url=url, edit=floors("1.0.0")) as opened:
            served = ask_paved(opened)
            assert isinstance(served, ServedProduct), getattr(served, "detail", served)
            assert paved_row(opened, served).child_schema_version == PRODUCT_VERSION == "1.1.0"
        with paved(tmp_path / "above", url=url, edit=floors("2.0.0")) as opened:
            refused = ask_paved(opened)
            assert isinstance(refused, RefusalEnvelope), refused
            row = paved_row(opened, refused)
            retained = json.loads(opened.record_of(refused).content_generation_path.assembly_refusal)["detail"]
    assert refused.reason == "child_admission"
    assert row.outcome_status == "ineligible" and row.producer_id == PRODUCER_ID
    assert "class-mismatch" in retained and "schema_version" in retained, retained
    assert "no-producing-skill" not in retained


def test_an_offer_floor_outside_the_requirements_lane_is_refused_at_open(tmp_path: pathlib.Path) -> None:
    def edit(config: dict[str, Any]) -> None:
        config["producers"]["spread"]["offers"][0]["versions_from"] = "2.0.0"

    with pytest.raises(ValueError, match="R-13"):
        paved(tmp_path, url="http://127.0.0.1:1/mcp", edit=edit)


def test_at_cp14s_own_tolerance_the_spread_is_withheld_and_the_composite_refuses(tmp_path: pathlib.Path, estate: None) -> None:
    """`OFC-G21`'s consumer side: estate truth, preserved across the boundary
    and across the road — the producer withholds at tolerance 0.25; the
    consumer records the `ineligible` row and refuses on its required slot."""
    with producer(estate) as url, paved(tmp_path, url=url, tolerance="0.25") as opened:
        refused = ask_paved(opened)
        assert isinstance(refused, RefusalEnvelope), refused
        row = paved_row(opened, refused)
    assert refused.reason == "child_admission"
    assert row.outcome_status == "ineligible" and row.child_content_address is None
    assert row.producer_id == PRODUCER_ID and row.producer_tenant == PRODUCER_TENANT


def test_a_severed_producer_and_a_wrong_identity_or_tenant_refuse_by_name(tmp_path: pathlib.Path, estate: None) -> None:
    """`OFC-G18` and `OFC-G22`'s consumer side. Only the consumer's declaration
    changes; the producer's bytes do not."""
    with paved(tmp_path / "severed", url="http://127.0.0.1:1/mcp") as opened:
        refused = ask_paved(opened)
        assert isinstance(refused, RefusalEnvelope), refused
        assert paved_row(opened, refused).refusal_ref == "producer-unavailable"
    with producer(estate) as url:
        for label, member, value, reason in (
            ("id", "producer_id", "someone-else", "producer-mismatch"),
            ("tenant", "producer_tenant", "another-tenant", "producer-tenant-mismatch"),
        ):
            def edit(config: dict[str, Any], member: str = member, value: str = value) -> None:
                config["producers"]["spread"][member] = value

            with paved(tmp_path / label, url=url, edit=edit) as opened:
                refused = ask_paved(opened)
                assert isinstance(refused, RefusalEnvelope), refused
                assert paved_row(opened, refused).refusal_ref == reason


def test_the_two_documents_carry_no_address_and_no_credential() -> None:
    for name in ("ccf_config.yaml", "ccf_environment.yaml"):
        text = (CONSUMER / name).read_text(encoding="utf-8")
        assert "http" not in text and "127.0.0.1" not in text and DEV_TOKEN not in text, name
