# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""An unreachable source, declared by the class, is refused as itself (`CP06C-F-06`; Dave, 2026-10-16 12:11, option B).

Before this, the only refusal a declared seam exception (`D-IMPL-347` B2) could
mint was ``subject-unavailable`` — *"the requested subject is not available to
this principal"* — which is false for an outage and reads to a credit officer as
a missing entitlement. The class now declares ``cause: source-unavailable`` and
the fabric records, discloses and replays a ``source-unavailable`` refusal.

The driver's own message can name hosts and ports, so it is the record's and an
entitled ``full`` reader's, never a ``minimal`` or ``reasoned`` caller's.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from ccf.products.contract import SUBJECT_WITHHOLDING_NEVER
from ccf.products.disclosure import EXTERNAL_STATEMENTS, disclose
from ccf.products.refusal import REFUSAL_KINDS, RefusalEnvelope, SourceUnavailableRefusal
from ccf.replay.engine import RefusalReplayOutcome
from ccf.replay.inspection import explain_decision
from ccf.replay.record import DecisionReplayRecord
from ccf_runtime.http_api.refusal_status import STATUS_FULFILLMENT_WITHHELD, status_for

from tests.products.test_paved_road import _config, _question, _write_tree
from tests.replay.test_replay_evidence_383 import _open_run

#: What a driver says when nothing listens — host and port included, as psycopg's does.
DRIVER_SAYS = 'connection to server at "10.9.8.7", port 5433 failed: Connection refused'


class SourceDown(Exception):
    """Stands in for a driver's connection error; matched by its exact name."""


class _Down:
    def __call__(self, context: object) -> tuple[()]:
        raise SourceDown(DRIVER_SAYS)


_NAME = f"{SourceDown.__module__}.{SourceDown.__qualname__}"


def _opened_with(tmp_path: pathlib.Path, cause: str):  # type: ignore[no-untyped-def]
    document = _config(subject_withholding=SUBJECT_WITHHOLDING_NEVER)
    document["product_class"]["seam_refusals"] = [
        {"exception": _NAME, "cause": cause, "error_code": "collateral-register-unreachable"}
    ]
    return _open_run(_write_tree(tmp_path, config=document), tmp_path / "evidence", acquire=_Down())


def _internal(opened, envelope: RefusalEnvelope) -> dict:  # type: ignore[no-untyped-def]
    address = opened.artifact_store.resolve_uri(uri=envelope.replay_reference)
    record = DecisionReplayRecord.model_validate_json(opened.artifact_store.get(content_address=address))
    return json.loads(record.content_generation_path.assembly_refusal)


def test_a_declared_outage_is_refused_as_source_unavailable_recorded_and_replayable(tmp_path: pathlib.Path) -> None:
    with _opened_with(tmp_path, "source-unavailable") as opened:
        envelope = opened.answer(_question(opened))

        assert isinstance(envelope, RefusalEnvelope)
        assert envelope.kind == envelope.reason == "source-unavailable"
        assert envelope.detail == EXTERNAL_STATEMENTS["source-unavailable"]
        assert "10.9.8.7" not in envelope.model_dump_json(), "the driver's text crossed at minimal"

        internal = _internal(opened, envelope)
        assert internal["kind"] == "source-unavailable"
        assert internal["detail"] == DRIVER_SAYS, "the record keeps the driver's own statement"

        address = opened.artifact_store.resolve_uri(uri=envelope.replay_reference)
        assert opened.evidence.incomplete() == [], "an outage is a finished decision, not an interrupted one"
        assert [e.refusal_reason for e in opened.evidence.decisions()] == ["source-unavailable"]
        assert isinstance(opened.replay_decision(address), RefusalReplayOutcome)
        explained = explain_decision(store=opened.artifact_store, evidence=opened.evidence, record_address=address)
        assert (explained.refusal_kind, explained.refusal_detail) == ("source-unavailable", DRIVER_SAYS)


def test_the_drivers_text_crosses_only_at_full(tmp_path: pathlib.Path) -> None:
    with _opened_with(tmp_path, "source-unavailable") as opened:
        internal = RefusalEnvelope.model_validate(_internal(opened, opened.answer(_question(opened))))
    assert internal.detail == DRIVER_SAYS

    for level in ("minimal", "reasoned"):
        shown, _ = disclose(internal, level=level, policy=None)  # type: ignore[arg-type]
        assert shown.kind == "source-unavailable", level
        assert "10.9.8.7" not in shown.model_dump_json(), level
    shown, _ = disclose(internal, level="full", policy=None)
    assert shown.detail == DRIVER_SAYS


def test_an_outage_is_answered_as_fulfillment_withheld_not_absent() -> None:
    """409, never 404 (nothing is absent) and never a 5xx (`D-IMPL-253` Q18)."""
    assert status_for("source-unavailable") == STATUS_FULFILLMENT_WITHHELD == 409
    assert status_for("subject-unavailable") == 404


@pytest.mark.parametrize("cause", ["nonexistent", "unauthorized", "undisclosed"])
def test_a_subject_cause_still_mints_subject_unavailable(tmp_path: pathlib.Path, cause: str) -> None:
    """Control: the three subject causes are unchanged."""
    with _opened_with(tmp_path, cause) as opened:
        envelope = opened.answer(_question(opened))
    assert isinstance(envelope, RefusalEnvelope) and envelope.kind == "subject-unavailable"


def test_the_token_collides_with_no_shipped_token() -> None:
    token = REFUSAL_KINDS[SourceUnavailableRefusal]
    others = [t for t in REFUSAL_KINDS.values() if t != token]
    assert not [t for t in others if t in token or token in t]
