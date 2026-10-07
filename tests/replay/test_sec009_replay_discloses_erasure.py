"""SEC-009 step (3) — replay over erased retained content stays POSITIVE, the erasure disclosed (`D-IMPL-374` (4)).

Design ``D-IMPL-367`` §5.2: a replay that meets an erased address does not
"not find" it. At the locked site — the retained child question — the outcome
is a typed ``ErasedContent`` member of the replay result, distinct from
``ReplayUnresolvable``; a replay whose inputs are intact and whose RETAINED
content is erased COMPLETES, with the erased members reported positively.

The decision: a composite refused at the delivery lane, whose child row
retains its exact question on the parent's store (``D-IMPL-342``). The
question is then erased; the reconstruction must still complete and say so.

RED today: the replay result has no disclosure layer — the reconstruction
either fails on the erased read or completes saying nothing about it.
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime

import pytest

from ccf.products.refusal import RefusalEnvelope
from ccf.replay.engine import replay_refusal
from ccf.replay.record import NO_FABRIC_READ
from tests.composition import composition_register
from tests.erasure import harness as h
from tests.products import test_d_impl_342_child_question_retention as q

pytestmark = [pytest.mark.crossproc]

ERASED_AT = datetime(2026, 7, 30, tzinfo=UTC)
RECORD_ADDRESS = "f" * 64


def test_replay_completes_with_erased_retained_content_reported_positively(tmp_path: pathlib.Path) -> None:
    opened, refused, record = q._ask_with_a_producer_that_then_exits(tmp_path, config=q._lane_floor_config())
    assert isinstance(refused, RefusalEnvelope), refused
    (row,) = record.content_generation_path.child_resolutions
    question = row.child_question_address
    assert question is not None and row.child_question_ref is not None
    tenant = record.tenant_id
    h.erasure("append_to_erasure_index")(
        opened.control_plane,
        composition_register(opened.control_plane, h.erasure("erasure_index_key")(tenant)),
        (
            h.erasure("ErasureIndexEntry")(
                content_address=question,
                erasure_record_address=RECORD_ADDRESS,
                reason="customer-request",
                erased_at=ERASED_AT,
            ),
        ),
    )
    fresh = q._fresh(opened)
    store = h.erasure("ErasureConsultingStore")(fresh, index=h.erasure("ErasureIndex")(opened.control_plane))
    reconstructed = replay_refusal(
        record_address=q._record_address(opened, refused, fresh), store=store,
        reader=q._NeverConsulted(), control_plane=opened.control_plane, environment=q._NeverConsulted(),  # type: ignore[arg-type]
    )
    # Positive: the decision reconstructs — its inputs are intact.
    assert reconstructed.graph_snapshot_id == NO_FABRIC_READ
    # And the erasure is DISCLOSED on the result, never an absence.
    erased = getattr(reconstructed, "erased_content", None)
    assert erased is not None, "MISSING CONTRACT: the replay result carries no erasure disclosure (SEC-009; D-IMPL-367 §5.2)"
    (member,) = erased
    assert member.content_address == question
    assert member.erasure_record_address == RECORD_ADDRESS
    assert member.site == "retained-child-question"
    # An unrelated reconstruction with nothing erased discloses nothing.
    clean = replay_refusal(
        record_address=q._record_address(opened, refused, fresh), store=fresh,
        reader=q._NeverConsulted(), control_plane=opened.control_plane, environment=q._NeverConsulted(),  # type: ignore[arg-type]
    )
    assert clean.erased_content == ()


def _erase(opened: object, address: str) -> None:
    control_plane = opened.control_plane  # type: ignore[attr-defined]
    h.erasure("append_to_erasure_index")(
        control_plane,
        composition_register(control_plane, h.erasure("erasure_index_key")(h.TENANT)),
        (
            h.erasure("ErasureIndexEntry")(
                content_address=address,
                erasure_record_address=RECORD_ADDRESS,
                reason="customer-request",
                erased_at=ERASED_AT,
            ),
        ),
    )


def _consulting(opened: object) -> object:
    return h.erasure("ErasureConsultingStore")(
        q._fresh(opened), index=h.erasure("ErasureIndex")(opened.control_plane)  # type: ignore[attr-defined]
    )


def _member(outcome: object, site: str, address: str) -> None:
    erased = getattr(outcome, "erased_content", None)
    assert erased, f"the replay result discloses no erasure: {outcome!r}"[:400]
    assert any(m.site == site and m.content_address == address and m.erasure_record_address == RECORD_ADDRESS for m in erased), erased


def test_replay_over_an_erased_child_contract_completes_with_the_erasure_disclosed(tmp_path: pathlib.Path) -> None:
    """Ruling 4: an erased ADMITTED CHILD CONTRACT is substituted by the erased
    reading and the replay completes positively — never refused by name."""
    from ccf.replay.engine import replay
    from ccf.replay.serve import ServedProduct

    opened, served, record = q._ask_with_a_producer_that_then_exits(tmp_path)
    assert isinstance(served, ServedProduct), served
    (row,) = record.content_generation_path.child_resolutions
    assert row.outcome_status == "admitted" and row.child_content_address is not None
    _erase(opened, row.child_content_address)
    outcome = replay(
        record_address=served.replay_ref.content_address, store=_consulting(opened),
        reader=q._NeverConsulted(), control_plane=opened.control_plane, environment=q._NeverConsulted(),  # type: ignore[arg-type]
    )
    assert outcome.record_content_address == served.replay_ref.content_address
    _member(outcome, "child-contract", row.child_content_address)


def test_replay_of_an_erased_decision_record_completes_with_the_erasure_disclosed(tmp_path: pathlib.Path) -> None:
    """Ruling 4: an erased DECISION RECORD is substituted by the erased reading
    and the replay completes positively — never refused by name."""
    opened, refused, _record = q._ask_with_a_producer_that_then_exits(tmp_path, config=q._lane_floor_config())
    fresh = q._fresh(opened)
    address = q._record_address(opened, refused, fresh)
    _erase(opened, address)
    outcome = replay_refusal(
        record_address=address, store=_consulting(opened),
        reader=q._NeverConsulted(), control_plane=opened.control_plane, environment=q._NeverConsulted(),  # type: ignore[arg-type]
    )
    assert outcome.record_content_address == address
    _member(outcome, "decision-record", address)
