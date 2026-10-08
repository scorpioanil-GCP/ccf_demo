"""`D-IMPL-341` — `expires_at` describes when the evidence stopped being current.

Dave's contract (2026-09-18): *"`expires_at` must describe when the evidence
stopped being current, not when the decision happened. A decision-time
anchor can overstate validity."* Until 2026-09-18 the governed path served
`decided_at + window` on every class and copied a declared
`ttl_anchor: from_entity_freshness` onto the contract unread (`CP03C-F-01`).

Every control here drives the paved road (`open_product`) over the paved
fixture's single product with ONE difference per control — the class's
declared anchor, the λ_c row's decay basis, or the instant the fixture's
source observed its claim — so the thing that moves `expires_at` is named by
the control that moves it. The five rulings R-1–R-5 are each held by a
control that says so.

| control | holds |
| --- | --- |
| C1 | R-1: an evidence-anchored class serves `expires_at == source instant + window` and `ttl_anchor_at == source instant` — not the decision instant, not the ingestion instant |
| C2 | R-1: with two observations the anchor is the freshest leading edge as of the decision instant; a later-dated observation does not leak into an earlier decision |
| C4 | R-3 row 1: the declaration over a table with no `valid-from` row is refused by name at open, and at the builder |
| C4b | R-3 row 1, widened (Dave, 2026-09-18): the declaration over NO table at all is refused at the builder, and a `from_decision` class over the same wiring is not |
| C4c | the same widening at the road's own registration moment: a config declaring the anchor with no `half_life` section is refused by `open_product` |
| C5 | R-3 row 2: a served set with no `valid_from` instant refuses `ttl-anchor-refusal` / `ttl-anchor-unresolvable` — nothing falls back |
| C6 | R-3 row 3: evidence older than the window refuses `ttl-refusal` / `ttl-bounds` with the anchored expiry named — distinct from C5 |
| C7 | R-2: a `from_decision` class serves exactly as before and states `ttl_anchor_at == decided_at` |
| C8 | F14: an evidence-anchored composite floors on `min(anchor + window, children)` and its rows carry the child's anchor and instant |
| C9 | R-5: replay re-derives the anchor over the re-executed view under the pinned table and holds it; a disagreeing derivation fails by name; a pre-341 record (member deleted from its bytes) reconstructs and is skipped BY NAME |
| C11 | `D-IMPL-31`'s mixing floor is measured from the DECISION instant, never from the evidence anchor — the review's one blocking finding |
| C12 | the builder holds its two clock keys to each other: two names for one table is a wiring defect and raises |
| C10 | the negative control: `expires_at <= decided_at + window` holds for the evidence-anchored product too, so it distinguishes nothing — it is recorded here so nobody mistakes it for coverage |

Sabotages S1–S8 are run by hand against this module and recorded in
`docs/D-IMPL-341-DESIGN.md` (as built).
"""

from __future__ import annotations

import copy
import hashlib
import json
import pathlib
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from tests.replay.authority import mechanism_put
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.signal.envelope import SignalEnvelope
from ccf.controlplane.artifacts import HalfLifeTable
from ccf.products.product import AcquisitionContext
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.products.expiry import (
    TTLAnchorResolution,
    TTLAnchorUndeclared,
    resolve_ttl_anchor,
)
from ccf.products.gates import GATE_TTL_ANCHOR, GATE_TTL_BOUNDS
from ccf.products.product import OpenedProduct, open_product
from ccf.products.refusal import RefusalEnvelope
from ccf.replay import engine as replay_engine
from ccf.replay.engine import (
    TTL_ANCHOR_NOT_RECORDED,
    ReplayDivergence,
    _hold_ttl_anchor,
    replay,
)
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from tests.deployment.test_replay_binding import ENTITY_CLASS
from tests.products import paved_fixture as fixture
from tests.products.paved_fixture import ADMITTED_AT, ASKED_AT, THRESHOLD_PARAMETER
from tests.composition import declare_wide_temporal_boundary, declared_erasure_trust

pytestmark = [pytest.mark.crossproc]

WINDOW = timedelta(hours=1)
CEILING = timedelta(hours=6)
#: The source's own instant on the fixture's claim — thirty minutes before the
#: question, so the evidence-anchored expiry sits strictly before the
#: decision-anchored one and the two cannot be confused.
OBSERVED = ASKED_AT - timedelta(minutes=30)


class _Acquire:
    """The fixture's acquisition with the source instant stated per entity."""

    def __init__(self, observed: Mapping[str, datetime | None]) -> None:
        self._observed = dict(observed)

    def __call__(self, context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
        return tuple(
            SignalEnvelope.model_validate(
                {
                    "tenant_id": context.tenant_id,
                    "envelope_id": f"envelope-{entity}",
                    "source": {"system_id": "fixture-system"},
                    "ingestion_timestamp": context.instant,
                    "observed_time": observed,
                    "raw_payload": {"account_ref": entity, "classification": "fixture-open", "label": entity},
                }
            )
            for entity, observed in self._observed.items()
        )


def _config(*, ttl_anchor: str, decay_basis: str | None) -> dict[str, Any]:
    document = fixture.producer_config()
    document = copy.deepcopy(document)
    document["product_class"]["ttl_anchor"] = ttl_anchor
    row = dict(document["half_life"][ENTITY_CLASS])
    if decay_basis is not None:
        row["decay_basis"] = decay_basis
    document["half_life"] = {ENTITY_CLASS: row}
    document["ttl"] = {"max_ttl_seconds": int(CEILING.total_seconds()), "product_ttl_seconds": int(WINDOW.total_seconds())}
    return document


def _open(tmp_path: pathlib.Path, *, ttl_anchor: str, decay_basis: str | None, observed: Mapping[str, datetime | None]) -> OpenedProduct:
    root = fixture.write_tree(tmp_path / "producer", config=_config(ttl_anchor=ttl_anchor, decay_basis=decay_basis), environment=fixture.producer_environment_text())
    return open_product(
        erasure_trust=declared_erasure_trust(),
        # The declared skills are granted through the ledger by an authorized principal
        # BEFORE opening: the paved road requests no grant (D-IMPL-354).
        control_plane=fixture.granted_control_plane(root),
        config_root=root, scratch=tmp_path / "scratch", acquire=_Acquire(observed), project=fixture.plan_factory,
        assess=fixture.assess, environ={fixture.CHILD_DSN_VAR: "postgresql://fixture"}, clock=lambda: ADMITTED_AT,
    )


def _ask(opened: OpenedProduct) -> Any:
    return opened.answer(opened.question(subject="acct-1", asked_at=ASKED_AT, intent="fixture-intent", freshness="fixture-freshness", parameters={THRESHOLD_PARAMETER: 1000}))


def _record(opened: OpenedProduct, outcome: Any) -> tuple[DecisionReplayRecord, FileArtifactStore, str]:
    # A read-back store under the deployment's OWN declaration: a record is
    # read only where the store shows the fabric's record writer filed it, and
    # which classes that writer files under is the declaration's to say
    # (`D-IMPL-378`). Declaring nothing would refuse every record it holds.
    fresh = FileArtifactStore(
        root=opened.scratch / opened.replay.store_dirname,
        write_kinds=opened.artifact_store.write_kinds,
    )
    address = outcome.replay_ref.content_address if isinstance(outcome, ServedProduct) else fresh.resolve_uri(uri=outcome.replay_reference)
    return DecisionReplayRecord.model_validate_json(fresh.get(content_address=address)), fresh, address


# --- C1 / C2 / C7 / C10 ------------------------------------------------------------------


def test_c1_an_evidence_anchored_class_expires_from_the_source_instant_not_the_decision(tmp_path: pathlib.Path) -> None:
    with _open(tmp_path, ttl_anchor="from_entity_freshness", decay_basis="valid-from", observed={"acct-1": OBSERVED}) as opened:
        served = _ask(opened)
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        record, _fresh, _address = _record(opened, served)
    product = served.product
    assert product.ttl_anchor == "from_entity_freshness"
    assert product.ttl_anchor_at == OBSERVED, "the anchor is the source's own instant"
    assert product.expires_at == OBSERVED + WINDOW
    assert product.expires_at != ASKED_AT + WINDOW, "not the decision instant (the defect)"
    assert product.expires_at != ADMITTED_AT + WINDOW and product.temporal_boundary == ASKED_AT
    # the record carries the anchor, and the λ_c table it anchored under is pinned
    assert record.content_generation_path.ttl_anchor_at == OBSERVED
    assert opened.keys is not None and opened.keys.half_life is not None
    assert any(b.key == opened.keys.half_life for b in record.policy_bindings.bindings), [b.key for b in record.policy_bindings.bindings]


def test_c2_the_anchor_is_the_freshest_leading_edge_as_of_the_decision_instant(tmp_path: pathlib.Path) -> None:
    older, newer, later = OBSERVED - timedelta(minutes=20), OBSERVED, ASKED_AT + timedelta(minutes=5)
    with _open(tmp_path, ttl_anchor="from_entity_freshness", decay_basis="valid-from", observed={"acct-1": older, "acct-2": newer, "acct-3": later}) as opened:
        served = _ask(opened)
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
    assert served.product.ttl_anchor_at == newer, "the freshest instant at or before the decision"
    assert served.product.expires_at == newer + WINDOW
    # a source instant dated after the decision instant is not evidence the decision had
    assert served.product.ttl_anchor_at != later


def test_c7_a_decision_anchored_class_serves_as_before_and_states_its_anchor(tmp_path: pathlib.Path) -> None:
    with _open(tmp_path, ttl_anchor="from_decision", decay_basis="valid-from", observed={"acct-1": OBSERVED}) as opened:
        served = _ask(opened)
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        record, _fresh, _address = _record(opened, served)
    assert served.product.ttl_anchor == "from_decision"
    assert served.product.expires_at == ASKED_AT + WINDOW
    assert served.product.ttl_anchor_at == ASKED_AT, "R-2: stated, never omitted on a new product"
    assert record.content_generation_path.ttl_anchor_at == ASKED_AT == record.recorded_at
    assert opened.keys is not None and not any(b.key == opened.keys.half_life for b in record.policy_bindings.bindings), "no table is pinned for a decision-anchored serve"


def test_c10_the_naive_bound_holds_for_the_anchored_product_and_proves_nothing(tmp_path: pathlib.Path) -> None:
    """NEGATIVE CONTROL, not an acceptance criterion. `expires_at <= decided_at
    + window` is true of the evidence-anchored product AND of the
    decision-anchored one, and it stays true under sabotage S1 (decision-time
    anchoring restored). A suite whose only expiry assertion had this shape
    would preserve the defect this decision ends."""
    with _open(tmp_path, ttl_anchor="from_entity_freshness", decay_basis="valid-from", observed={"acct-1": OBSERVED}) as opened:
        served = _ask(opened)
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
    assert served.product.expires_at <= ASKED_AT + WINDOW  # holds either way — see the docstring


# --- C4 / C5 / C6 -------------------------------------------------------------------------


def test_c4_a_declaration_no_row_could_honor_is_refused_by_name_at_open_and_at_the_builder(tmp_path: pathlib.Path) -> None:
    """R-3, first row. The paved road refuses at OPEN — before any question —
    and a resolver wired by hand over a fabric booted on the low road refuses
    at the builder, by the same predicate and the same name. Neither serves a
    decision-anchored expiry under an evidence-anchored label."""
    with pytest.raises(TTLAnchorUndeclared, match="declares no row with `decay_basis: valid-from`"):
        _open(tmp_path / "a", ttl_anchor="from_entity_freshness", decay_basis=None, observed={"acct-1": OBSERVED})
    with pytest.raises(TTLAnchorUndeclared, match="observed-at"):
        _open(tmp_path / "b", ttl_anchor="from_entity_freshness", decay_basis="observed-at", observed={"acct-1": OBSERVED})
    # the builder, over a fabric the low road booted from the refused tree
    from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: PLC0415
    from ccf.deployment import load_config_and_boot  # noqa: PLC0415
    from ccf.products.resolver import build_governed_resolver  # noqa: PLC0415

    refused_root = fixture.write_tree(tmp_path / "hand", config=_config(ttl_anchor="from_entity_freshness", decay_basis=None), environment=fixture.producer_environment_text())
    with _open(tmp_path / "template", ttl_anchor="from_decision", decay_basis=None, observed={"acct-1": OBSERVED}) as template:
        fabric = template._boot()
        try:
            arguments = template.build_arguments(fabric)
        finally:
            fabric.handle.close()
    registry = ControlPlaneRegistry()
    hand = load_config_and_boot(refused_root / "ccf_config.yaml", registry=registry, connection={"database_path": str(tmp_path / "hand.sqlite3")})
    # `D-IMPL-358` step 5 ruling 11: a deployment declaring no temporal boundary
    # refuses every question, so a fixture that means to serve declares one.
    declare_wide_temporal_boundary(registry, tenant_id=hand.tenant_id)
    try:
        with pytest.raises(TTLAnchorUndeclared, match="declares no row with `decay_basis: valid-from`"):
            build_governed_resolver(**{**arguments, "fabric": hand, "control_plane": registry})
    finally:
        hand.handle.close()


def test_c5_a_served_set_with_no_source_instant_refuses_by_its_own_reason(tmp_path: pathlib.Path) -> None:
    with _open(tmp_path, ttl_anchor="from_entity_freshness", decay_basis="valid-from", observed={"acct-1": None}) as opened:
        refused = _ask(opened)
        assert isinstance(refused, RefusalEnvelope), refused
        record, _fresh, _address = _record(opened, refused)
    assert refused.kind == "ttl-anchor-refusal" and refused.reason == GATE_TTL_ANCHOR
    assert refused.kind != "ttl-refusal" and refused.reason != GATE_TTL_BOUNDS
    block = json.loads(record.content_generation_path.assembly_refusal)
    assert json.loads(block["fields"]["valid_from_rows"]) == [ENTITY_CLASS]
    assert ENTITY_CLASS in json.loads(block["fields"]["observation_types"])
    assert record.content_generation_path.ttl_anchor_at is None, "nothing was anchored, so nothing is claimed"


def test_c6_evidence_older_than_the_window_refuses_ttl_bounds_naming_the_anchored_expiry(tmp_path: pathlib.Path) -> None:
    stale = ASKED_AT - timedelta(hours=2)
    with _open(tmp_path, ttl_anchor="from_entity_freshness", decay_basis="valid-from", observed={"acct-1": stale}) as opened:
        refused = _ask(opened)
        assert isinstance(refused, RefusalEnvelope), refused
        record, _fresh, _address = _record(opened, refused)
    assert refused.kind == "ttl-refusal" and refused.reason == GATE_TTL_BOUNDS
    assert refused.kind != "ttl-anchor-refusal"
    block = json.loads(record.content_generation_path.assembly_refusal)
    assert json.loads(block["fields"]["expires_at"]) == (stale + WINDOW).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    # `D-IMPL-358` step 5 section H. MIGRATED with the comparand: this asserted
    # `ASKED_AT`. Gate 3's `now` is the instant it actually applies its bound at,
    # and that is the moment of SERVICE. The old assertion was pinning the defect —
    # it said the gate compared against the question's instant, and it did, which
    # is why a product already expired at hand-over could be served.
    assert json.loads(block["fields"]["now"]) == fixture.ADMITTED_AT.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# --- C8 ------------------------------------------------------------------------------------


def test_c8_an_evidence_anchored_composite_floors_on_its_anchor_and_its_children(tmp_path: pathlib.Path) -> None:
    from tests.products.test_paved_consumer import _environ, _producer, _question, _the_row  # noqa: PLC0415

    # The parent's own term must be the BINDING one, or a decision-anchored own
    # term (sabotage S6) would hide behind the child's floor: the parent's
    # evidence is five minutes old and its window twelve minutes, so its own
    # term ends seven minutes after the question — before the child's ten-minute
    # window does — while a decision-anchored own term would end after it.
    # `D-IMPL-358` step 5 section H: FOURTEEN minutes, not twelve. With evidence
    # five minutes old, a twelve-minute window ends at ASKED_AT + 7min — exactly
    # the instant this fixture serves at — and Gate 3's lower bound is strict
    # (`now < expires_at`), so the parent refused itself before its own subject
    # was reached. Fourteen ends at +9min: clear of the serving instant, and still
    # BEFORE the child's ten-minute window, which is the premise below.
    parent_observed, parent_window = ASKED_AT - timedelta(minutes=5), timedelta(minutes=14)
    config = fixture.consumer_config()
    config["product_class"]["ttl_anchor"] = "from_entity_freshness"
    row = dict(config["half_life"][ENTITY_CLASS]); row["decay_basis"] = "valid-from"
    config["half_life"] = {ENTITY_CLASS: row}
    config["ttl"] = {"max_ttl_seconds": int(CEILING.total_seconds()), "product_ttl_seconds": int(parent_window.total_seconds())}
    root = fixture.write_tree(tmp_path / "consumer", config=config, environment=fixture.consumer_environment_text())
    with _producer() as url, open_product(
        erasure_trust=declared_erasure_trust(),
        control_plane=fixture.granted_control_plane(root),  # grants in force before opening (D-IMPL-354)
        config_root=root, scratch=tmp_path / "scratch", acquire=_Acquire({"acct-1": parent_observed}), project=fixture.plan_factory,
        assess=fixture.assess, questions=fixture.questions, environ=_environ(url), clock=lambda: ADMITTED_AT,
    ) as opened:
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        row_ = _the_row(opened, served)
    parent = served.product
    assert parent.ttl_anchor == "from_entity_freshness" and parent.ttl_anchor_at == parent_observed
    # the child is decision-anchored on the composite's asked instant; its window is the producer's (600 s)
    assert row_.child_ttl_anchor == "from_decision" and row_.child_ttl_anchor_at == ASKED_AT
    assert row_.child_expires_at is not None and row_.child_expires_at == ASKED_AT + timedelta(seconds=600)
    assert parent_observed + parent_window < row_.child_expires_at < ASKED_AT + parent_window, "the premise: the parent's own term binds"
    assert parent.expires_at == parent_observed + parent_window == min(parent_observed + parent_window, row_.child_expires_at)
    assert parent.expires_at != min(ASKED_AT + parent_window, row_.child_expires_at), "a decision-anchored own term would end with the child"


def test_c4b_an_evidence_anchor_over_no_table_at_all_is_refused_at_the_builder(tmp_path: pathlib.Path) -> None:
    """R-3's first row, widened by Dave's ruling of 2026-09-18: a resolver wired
    with NO λ_c table at all — neither key given — cannot ever resolve an
    evidence instant, so an evidence-anchored class is refused where the wiring
    is done rather than at every question it is later asked.

    The boundary this keeps: missing CONFIGURATION fails at the builder; a
    sound configuration whose OBSERVATIONS supply no instant fails at serve time
    (C5); an anchor whose window has passed fails at the expiry gate (C6).
    """
    from ccf.products.resolver import build_governed_resolver  # noqa: PLC0415

    with _open(tmp_path / "t", ttl_anchor="from_entity_freshness", decay_basis="valid-from", observed={"acct-1": OBSERVED}) as template:
        fabric = template._boot()
        try:
            arguments = template.build_arguments(fabric)
            assert arguments["evidence_clock_key"] is not None, "the road stopped passing the clock key"
            with pytest.raises(TTLAnchorUndeclared, match="wired with no λ_c table"):
                build_governed_resolver(**{**arguments, "evidence_clock_key": None, "half_life_key": None})
        finally:
            fabric.handle.close()
    # A DECISION-ANCHORED class over the same wiring is untouched: the rule is
    # about the anchor a class declares, not about tables.
    with _open(tmp_path / "d", ttl_anchor="from_decision", decay_basis="valid-from", observed={"acct-1": OBSERVED}) as plain_template:
        plain_fabric = plain_template._boot()
        try:
            plain_arguments = plain_template.build_arguments(plain_fabric)
            plain = build_governed_resolver(**{**plain_arguments, "evidence_clock_key": None, "half_life_key": None})
            assert plain.half_life_key is None
        finally:
            plain_fabric.handle.close()


def test_c4c_the_road_refuses_an_evidence_anchor_with_no_half_life_section_at_open(tmp_path: pathlib.Path) -> None:
    """Ruling 3's OTHER boundary. `C4b` holds the builder; the paved road's own
    registration moment is `open_product`, and a config that declares the
    anchor while carrying no `half_life` section at all is refused there — by
    name, before a question, and naming the absent section rather than a row.
    """
    document = _config(ttl_anchor="from_entity_freshness", decay_basis="valid-from")
    document.pop("half_life")
    root = fixture.write_tree(tmp_path / "producer", config=document, environment=fixture.producer_environment_text())
    with pytest.raises(TTLAnchorUndeclared, match="no half_life section"):
        open_product(
            erasure_trust=declared_erasure_trust(),
            control_plane=fixture.granted_control_plane(root),  # grants in force before opening (D-IMPL-354)
            config_root=root, scratch=tmp_path / "scratch", acquire=_Acquire({"acct-1": OBSERVED}),
            project=fixture.plan_factory, assess=fixture.assess,
            environ={fixture.CHILD_DSN_VAR: "postgresql://fixture"}, clock=lambda: ADMITTED_AT,
        )


# --- C11: the two instants, two laws (the review's blocking finding) ------------------------


@pytest.mark.parametrize(
    "floor_seconds,serves",
    [(240, False), (120, True)],
    ids=["breached-at-the-evaluation-instant", "met-at-the-evaluation-instant"],
)
def test_c11_a_composites_mixing_floor_is_measured_from_the_evaluation_instant(
    tmp_path: pathlib.Path, floor_seconds: int, serves: bool
) -> None:
    """`D-IMPL-31`'s mixing law measures how much validity a child has LEFT.

    **MIGRATED by `D-IMPL-358` step 5 section I, and strictly strengthened.**
    This read *"a fact about the DECISION instant"* and measured from
    `decided_at`. Section I made the measuring instant `served_at` — the moment
    the answer is handed over — and renamed the parameter to `evaluated_at` with
    the value, because how much validity a child has left is a fact about when
    the consumer receives it, not about when the parent's question was decided.

    The review of `D-IMPL-341` found the anchor and the instant sharing one
    argument: the resolver passed the evidence anchor as `compose_children`'s
    only instant and `refuse_mixing` read it as `evaluated_at`, so every
    constituent's remaining validity was overstated by `decided_at -
    ttl_anchor_at` and a child breaching its declared floor composed anyway.

    **The arithmetic, every instant MEASURED from the fixture rather than
    assumed** — and this is why the migration makes the control sharper. The
    parent's evidence is at 11:55, the question is asked at 12:00, the answer is
    served at 12:07, and the child's window ends at 12:10. So the child has

        FIFTEEN minutes left at the evidence anchor,
        TEN at the decision instant,
        THREE at the instant it is actually served.

    A floor of FOUR minutes must REFUSE and one of TWO must SERVE. The old pair
    (twelve and nine minutes) could only tell the anchor from the decision; this
    pair separates all three readings, so a regression to EITHER of the two
    superseded instants turns it red rather than only one of them.
    """
    from tests.products.test_paved_consumer import _environ, _producer, _question, _the_row  # noqa: PLC0415

    # `D-IMPL-358` step 5 section H: FOURTEEN minutes, not twelve. With evidence
    # five minutes old, a twelve-minute window ends at ASKED_AT + 7min — exactly
    # the instant this fixture serves at — and Gate 3's lower bound is strict
    # (`now < expires_at`), so the parent refused itself before its own subject
    # was reached. Fourteen ends at +9min: clear of the serving instant, and still
    # BEFORE the child's ten-minute window, which is the premise below.
    parent_observed, parent_window = ASKED_AT - timedelta(minutes=5), timedelta(minutes=14)
    config = fixture.consumer_config()
    config["product_class"]["ttl_anchor"] = "from_entity_freshness"
    config["product_class"]["constituent_validity_floors"] = {
        "min_validity_seconds_by_signal": {fixture.CHILD_CLASS: floor_seconds}
    }
    row = dict(config["half_life"][ENTITY_CLASS]); row["decay_basis"] = "valid-from"
    config["half_life"] = {ENTITY_CLASS: row}
    config["ttl"] = {"max_ttl_seconds": int(CEILING.total_seconds()), "product_ttl_seconds": int(parent_window.total_seconds())}
    root = fixture.write_tree(tmp_path / "consumer", config=config, environment=fixture.consumer_environment_text())
    with _producer() as url, open_product(
        erasure_trust=declared_erasure_trust(),
        control_plane=fixture.granted_control_plane(root),  # grants in force before opening (D-IMPL-354)
        config_root=root, scratch=tmp_path / "scratch", acquire=_Acquire({"acct-1": parent_observed}), project=fixture.plan_factory,
        assess=fixture.assess, questions=fixture.questions, environ=_environ(url), clock=lambda: ADMITTED_AT,
    ) as opened:
        outcome = opened.answer(_question(opened))
        if serves:
            assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
            row_ = _the_row(opened, outcome)
            # The premise, asserted rather than assumed: the child's remaining
            # validity differs by clock, and the floor is met only at the
            # decision instant — so the serving case is not vacuous either.
            record, _fresh, _address = _record(opened, outcome)
            assert row_.child_expires_at == ASKED_AT + timedelta(seconds=600)
            assert row_.child_expires_at - record.recorded_at == timedelta(minutes=10), "the remaining validity at the decision instant"
            assert row_.child_expires_at - parent_observed == timedelta(minutes=15), "and at the evidence anchor — the gap the law must not read"
            assert timedelta(seconds=floor_seconds) <= timedelta(minutes=10), "the serving case must be met at the DECISION instant"
            assert outcome.product.ttl_anchor_at == parent_observed, "the expiry still runs from the evidence"
        else:
            assert isinstance(outcome, RefusalEnvelope), getattr(outcome, "product", outcome)
            assert outcome.kind == "composite-child-refusal", (outcome.kind, outcome.reason)
            record, _fresh, _address = _record(opened, outcome)
            assert record.recorded_at == ASKED_AT, "the fixture's decision instant moved; the arithmetic above is stale"
            block = json.loads(record.content_generation_path.assembly_refusal)
            assert "declared validity floor" in block["detail"], block["detail"]
            assert json.loads(block["fields"]["reason"]) == "mixing-refused", block["fields"]
            # `D-IMPL-358` step 5 section I: the refusal names the EVALUATION
            # instant. It named `recorded_at` (the decision) until the mixing law's
            # instant moved to `served_at`. Both superseded readings are refused
            # below rather than only one, which is what makes this pair able to
            # catch a regression to EITHER of them.
            assert fixture.ADMITTED_AT.isoformat() in block["detail"], "the refusal names an instant other than the evaluation"
            assert record.recorded_at.isoformat() not in block["detail"], "the mixing law read the decision instant"
            assert parent_observed.isoformat() not in block["detail"], "the mixing law read the evidence anchor"


# --- C12: the builder's two keys cannot disagree silently -----------------------------------


def test_c12_the_builder_refuses_two_disagreeing_clock_keys_and_accepts_one_name_twice(tmp_path: pathlib.Path) -> None:
    """`half_life_key` and `evidence_clock_key` name the same manifest key from
    two callers — the scorer's table and the anchor's clock are one table, and
    the builder holds them to each other rather than silently preferring one.
    Two names is a wiring defect and raises; one name given twice builds.
    """
    from ccf.products.resolver import build_governed_resolver  # noqa: PLC0415

    with _open(tmp_path / "t", ttl_anchor="from_decision", decay_basis="valid-from", observed={"acct-1": OBSERVED}) as template:
        fabric = template._boot()
        try:
            arguments = template.build_arguments(fabric)
            assert arguments["evidence_clock_key"] is not None, "the road stopped passing the clock key"
            with pytest.raises(TypeError, match="D-IMPL-341"):
                build_governed_resolver(**{**arguments, "half_life_key": "somebody-elses-table"})
            # And the road's own construction — the clock key alone, beside a
            # supplied scorer — resolves to that one key on the resolver, which
            # is what makes the two names one table rather than two.
            built = build_governed_resolver(**arguments)
            assert built.half_life_key == arguments["evidence_clock_key"]
            # The same name given twice is not a disagreement and is refused
            # only for the reason it really is: a scorer and the reference
            # material are alternatives (the builder's own rule, not 341's).
            with pytest.raises(TypeError, match="alternatives rather than layers"):
                build_governed_resolver(**{**arguments, "half_life_key": arguments["evidence_clock_key"]})
        finally:
            fabric.handle.close()


# --- C9 ------------------------------------------------------------------------------------


class _Environment:
    """A replay environment over the paved fixture, built from the record and the
    deployment's own documents — the same shape cp-06-canonical's suite builds."""

    def __init__(self, *, opened: OpenedProduct, fabric: Any, record: DecisionReplayRecord, window: timedelta, ttl_anchor: str, carry_anchor: bool) -> None:
        from ccf.deployment.operators import build_operator_registry  # noqa: PLC0415
        from ccf.products.provenance import EffectiveRequest  # noqa: PLC0415
        from ccf.products.resolver import build_governed_resolver  # noqa: PLC0415

        path = record.content_generation_path
        assert path.request is not None
        resolution = record.policy_bindings.request_resolution
        effective = EffectiveRequest.model_validate_json(resolution) if isinstance(resolution, str) else resolution
        assert isinstance(effective, EffectiveRequest)
        self._request = path.request.model_copy(update={"parameters": dict(effective.values())})
        self._required = tuple(path.operator_plan)
        arguments = opened.build_arguments(fabric)
        self._policy_key = arguments["policy_bundle_key"]
        self._window = window
        self._ttl_anchor = ttl_anchor
        self._carry = carry_anchor
        resolver = build_governed_resolver(**arguments)
        self._operators = build_operator_registry(
            parameters=resolver.operator_parameters(self._request),
            view=fabric.handle.reader.as_of(tenant_id=record.tenant_id, at=record.context_fabric_snapshot.temporal_boundary),
            pins=fabric.pins, policy_bundle_key=self._policy_key,
        )

    def resolve_plan(self, *, plan_id: str) -> Any:
        return fixture.plan_factory(required=self._required, request=self._request)

    def resolve_operators(self, *, operator_keys: tuple[str, ...]) -> Any:
        return self._operators

    def rehydrate_product(self, *, record: DecisionReplayRecord, projection: Any) -> ContextProductContract:
        path, snapshot = record.content_generation_path, record.context_fabric_snapshot
        # R-5 / compatibility: a record carrying the anchor is rebuilt from it; a
        # record without one is the pre-341 shape — decision-anchored expiry
        # under whatever the class declared, and no `ttl_anchor_at` — exactly
        # the envelope such a record described when it was written.
        anchor = path.ttl_anchor_at if self._carry else None
        return ContextProductContract(
            schema_name=self._request.schema_name, schema_version=self._request.schema_version, plan_id=projection.plan_id,
            tenant_id=record.tenant_id, temporal_boundary=snapshot.temporal_boundary,
            expires_at=(anchor if anchor is not None else record.recorded_at) + self._window,
            ttl_anchor=self._ttl_anchor,  # type: ignore[arg-type]
            ttl_anchor_at=anchor,
            lineage=ProductLineage(
                operators_invoked=frozenset(path.operator_plan),
                policy_bundle_versions=frozenset(b.version for b in record.policy_bindings.bindings if b.key == self._policy_key),
                graph_snapshot_at=snapshot.temporal_boundary,
            ),
            payload=projection.payload, debt=path.debt, debt_evidence=path.debt_evidence,
            source_refresh_recency=path.source_refresh_recency, obligation_in_force=path.obligation_in_force,
        )


def _reopened(opened: OpenedProduct) -> Any:
    from ccf.deployment import load_config_and_boot  # noqa: PLC0415

    minted = sorted(opened.scratch.glob("paved_child*.sqlite3"))[-1]
    return load_config_and_boot(opened.config_path, registry=opened.control_plane, connection={"database_path": str(minted)})


def test_c9_replay_re_derives_the_anchor_and_a_pre_341_record_is_skipped_by_name(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with _open(tmp_path, ttl_anchor="from_entity_freshness", decay_basis="valid-from", observed={"acct-1": OBSERVED}) as opened:
        served = _ask(opened)
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        record, fresh, address = _record(opened, served)
        fabric = _reopened(opened)
        try:
            environment = _Environment(opened=opened, fabric=fabric, record=record, window=WINDOW, ttl_anchor="from_entity_freshness", carry_anchor=True)
            # R-5, positive: the anchor re-derived over the re-executed view equals the record's
            outcome = replay(record_address=address, store=fresh, reader=fabric.handle.reader, control_plane=opened.control_plane, environment=environment)
            assert content_hash(outcome.product) == record.content_generation_path.product_content_address
            assert outcome.product.ttl_anchor_at == OBSERVED
            # R-5, negative: a derivation that disagrees fails replay by name — nothing is overwritten
            genuine = replay_engine.resolve_ttl_anchor

            def disagreeing(**kwargs: Any) -> Any:
                resolved = genuine(**kwargs)
                assert isinstance(resolved, TTLAnchorResolution)
                return resolved.model_copy(update={"anchor_at": resolved.anchor_at - timedelta(minutes=1)})

            monkeypatch.setattr(replay_engine, "resolve_ttl_anchor", disagreeing)
            with pytest.raises(ReplayDivergence, match="re-derived over the re-executed view"):
                replay(record_address=address, store=fresh, reader=fabric.handle.reader, control_plane=opened.control_plane, environment=environment)
            monkeypatch.undo()
            assert DecisionReplayRecord.model_validate_json(fresh.get(content_address=address)) == record, "the record was not touched"
            # THE PRE-341 SHAPE, AS BYTES: the member deleted from the record, and the
            # record naming the product such a record described — the class's
            # declared anchor recorded and not computed, `expires_at` run from the
            # decision instant, no `ttl_anchor_at` (`CP03C-F-01` exactly). Filed at
            # its own address. The environment rebuilds that envelope, every other
            # replay check runs, and the anchor hold alone is skipped BY NAME.
            product_then = served.product.model_copy(update={"ttl_anchor_at": None, "expires_at": record.recorded_at + WINDOW})
            assert product_then.ttl_anchor == "from_entity_freshness" and product_then.ttl_anchor_at is None
            older = json.loads(canonical_bytes(record))
            older["content_generation_path"].pop("ttl_anchor_at")
            older["content_generation_path"]["product_content_address"] = content_hash(product_then)
            older_bytes = json.dumps(older, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            older_record = DecisionReplayRecord.model_validate_json(older_bytes)
            assert older_record.content_generation_path.ttl_anchor_at is None
            older_address = hashlib.sha256(older_bytes).hexdigest()
            assert content_hash(older_record) == older_address, "a record lacking the member reloads to its own address"
            # Filed as the deployment's writer filed the genuine record — by
            # mechanism, under the same tenant and record class — and checked
            # byte-for-byte: a record is read only where the store shows the
            # record writer filed it (`D-IMPL-378`).
            (genuine_filing,) = fresh.names_at(content_address=address)
            filed = mechanism_put(
                fresh, tenant=genuine_filing.tenant_id, artifact_class=genuine_filing.artifact_class,
                name=older_address, artifact=json.loads(older_bytes),
            )
            assert filed.content_address == older_address and fresh.get(content_address=older_address) == older_bytes
            plain = _Environment(opened=opened, fabric=fabric, record=older_record, window=WINDOW, ttl_anchor="from_entity_freshness", carry_anchor=False)
            older_outcome = replay(record_address=older_address, store=fresh, reader=fabric.handle.reader, control_plane=opened.control_plane, environment=plain)
            assert older_outcome.product.ttl_anchor_at is None and older_outcome.product.expires_at == record.recorded_at + WINDOW
            assert content_hash(older_outcome.product) == content_hash(product_then)
            assert _hold_ttl_anchor(record=older_record, product=older_outcome.product, execution=None, control_plane=opened.control_plane) == TTL_ANCHOR_NOT_RECORDED  # type: ignore[arg-type]
        finally:
            fabric.handle.close()
