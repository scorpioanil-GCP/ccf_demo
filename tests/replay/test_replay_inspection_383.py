# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The four bank questions, answered from retained evidence (`D-IMPL-383`; Dave, 2026-10-16).

*"Why was this request refused?" "Which policies and data supported this
answer?" "Show decisions involving this company last Tuesday." "Replay this
decision and verify that it reproduces."* Each is asked here of a SECOND opening
of the evidence root — the restarted service, its acquisition sabotaged — so an
answer can only have come from what was retained.

The explanation is checked against the decision record it claims to restate,
never against fixed text, and the verbs against their exit statuses.
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest

from ccf.products.product import OpenedProduct
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.evidence import ReplayEvidenceUnavailable
from ccf.replay.inspection import explain_decision
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf_runtime.cli import evidence as verbs

from tests.products.test_paved_road import _question, _write_tree
from tests.replay.test_replay_evidence_383 import _SourcesUnavailable, _address, _early_refusal, _open_run


@pytest.fixture()
def retained(tmp_path: pathlib.Path) -> Iterator[tuple[OpenedProduct, dict[str, str]]]:
    """Three decisions answered by one run; yielded through a restarted run that cannot reach a source."""
    root, evidence = _write_tree(tmp_path), tmp_path / "evidence-root"
    with _open_run(root, evidence) as opened:
        served = opened.answer(_question(opened))
        after = opened.answer(_question(opened, no_such_parameter=1))
        assert isinstance(served, ServedProduct) and isinstance(after, RefusalEnvelope)
        addresses = {
            "served": _address(opened, served),
            "after": _address(opened, after),
            "before": _address(opened, _early_refusal(opened)),
        }
    with _open_run(root, evidence, acquire=_SourcesUnavailable()) as restarted:
        yield restarted, addresses


def _record(opened: OpenedProduct, address: str) -> DecisionReplayRecord:
    return DecisionReplayRecord.model_validate_json(opened.artifact_store.get(content_address=address))


def _explain(opened: OpenedProduct, address: str):  # type: ignore[no-untyped-def]
    return explain_decision(store=opened.artifact_store, evidence=opened.evidence, record_address=address)


def _run(opened: OpenedProduct, *argv: str) -> tuple[int, str]:
    parser = argparse.ArgumentParser()
    verbs.register(parser.add_subparsers(dest="command", required=True))
    out = io.StringIO()
    return verbs.run(parser.parse_args(list(argv)), opened, out=out), out.getvalue()


# --- "Which policies and data supported this answer?" -------------------------------------


def test_a_served_decision_is_explained_by_its_own_policy_bindings_inputs_and_snapshot(retained) -> None:  # type: ignore[no-untyped-def]
    opened, addresses = retained
    explained = _explain(opened, addresses["served"])
    record = _record(opened, addresses["served"])

    assert explained.outcome == "served"
    assert (explained.refusal_reason, explained.refusal_detail) == (None, None)
    assert [(p.key, p.version) for p in explained.policies] == [
        (b.key, b.version) for b in record.policy_bindings.bindings
    ], "every binding in force, at its pinned version, in the record's order"
    resolved = json.loads(record.policy_bindings.request_resolution)["parameters"]
    assert [(p.name, p.authority) for p in explained.parameters] == [(r["name"], r["authority"]) for r in resolved]
    assert explained.read_graph
    assert explained.graph_snapshot_id == record.context_fabric_snapshot.graph_snapshot_id
    assert explained.as_of == record.context_fabric_snapshot.temporal_boundary
    assert explained.entities_touched == len(record.context_fabric_snapshot.touched_entities) > 0
    assert explained.relationships_touched == len(record.context_fabric_snapshot.touched_relationships)


# --- "Why was this request refused?" ---------------------------------------------------------


def test_a_refusal_is_explained_by_the_sentence_written_when_it_refused(retained) -> None:  # type: ignore[no-untyped-def]
    opened, addresses = retained
    explained = _explain(opened, addresses["after"])
    block = json.loads(_record(opened, addresses["after"]).content_generation_path.assembly_refusal)

    assert explained.outcome == "refused"
    assert explained.refusal_reason == opened.evidence.entry(addresses["after"]).refusal_reason  # type: ignore[union-attr]
    assert explained.refusal_detail == block["detail"] and explained.refusal_detail
    assert explained.refusal_kind == block["kind"]


def test_a_refusal_before_any_graph_says_it_read_no_data(retained) -> None:  # type: ignore[no-untyped-def]
    opened, addresses = retained
    explained = _explain(opened, addresses["before"])

    assert explained.outcome == "refused" and explained.refusal_reason == "class-mismatch"
    assert "no.such-class" in (explained.refusal_detail or "")
    assert explained.read_graph is False
    assert (explained.graph_snapshot_id, explained.as_of, explained.entities_touched) == (None, None, None)


def test_a_decision_whose_graph_is_gone_is_still_explained_but_does_not_replay(retained) -> None:  # type: ignore[no-untyped-def]
    opened, addresses = retained
    entry = opened.evidence.entry(addresses["served"])
    assert entry is not None
    opened.evidence.graph_path(entry).unlink()

    assert _explain(opened, addresses["served"]).outcome == "served"
    status, printed = _run(opened, "replay", addresses["served"])
    assert status == verbs.UNAVAILABLE and printed.startswith("UNAVAILABLE:"), printed


def test_an_unknown_decision_is_unavailable(retained) -> None:  # type: ignore[no-untyped-def]
    opened, _ = retained
    with pytest.raises(ReplayEvidenceUnavailable):
        _explain(opened, "0" * 64)


# --- "Show decisions involving this company last Tuesday." -----------------------------------


def test_decisions_lists_by_identifier_and_by_day(retained) -> None:  # type: ignore[no-untyped-def]
    opened, addresses = retained
    subject = opened.evidence.entry(addresses["served"]).subject  # type: ignore[union-attr]
    today = datetime.now(UTC).astimezone().date()

    status, printed = _run(opened, "decisions", "--involving", subject, "--since", today.isoformat())
    assert status == verbs.ANSWERED
    assert all(address in printed for address in addresses.values()), printed
    assert "class-mismatch" in printed

    status, printed = _run(opened, "decisions", "--until", (today - timedelta(days=1)).isoformat())
    assert status == verbs.ANSWERED and not any(address in printed for address in addresses.values()), printed

    status, printed = _run(opened, "decisions", "--involving", "NO-SUCH-IDENTIFIER")
    assert not any(address in printed for address in addresses.values()), printed

    status, printed = _run(opened, "decisions", "--json")
    assert {entry["record_address"] for entry in json.loads(printed)} == set(addresses.values())


def test_a_malformed_date_is_refused(retained) -> None:  # type: ignore[no-untyped-def]
    opened, _ = retained
    status, printed = _run(opened, "decisions", "--since", "last tuesday")
    assert status == verbs.MALFORMED and printed.startswith("REFUSED:"), printed


# --- "Replay this decision and verify that it reproduces." -----------------------------------


@pytest.mark.parametrize("name", ["served", "after", "before"])
def test_replay_reproduces_every_retained_decision_by_a_prefix_of_its_address(retained, name) -> None:  # type: ignore[no-untyped-def]
    opened, addresses = retained
    status, printed = _run(opened, "replay", addresses[name][:12])
    assert status == verbs.ANSWERED and printed.startswith("REPRODUCED:"), printed
    assert addresses[name] in printed


def test_why_prints_the_refusal_sentence_and_a_short_prefix_is_refused(retained) -> None:  # type: ignore[no-untyped-def]
    opened, addresses = retained
    status, printed = _run(opened, "why", addresses["after"][:10])
    assert status == verbs.ANSWERED
    assert _explain(opened, addresses["after"]).refusal_detail in printed

    status, printed = _run(opened, "why", addresses["after"][:4])
    assert status == verbs.MALFORMED, printed


# --- an auditor needs no source credential (`CP06C-F-07`) -------------------------------------


def _held(evidence: pathlib.Path) -> list[str]:
    return sorted(str(p.relative_to(evidence)) for p in evidence.rglob("*") if p.is_file())


def test_an_opening_without_source_settings_replays_and_explains_every_decision(tmp_path: pathlib.Path) -> None:
    root, evidence = _write_tree(tmp_path), tmp_path / "evidence-root"
    with _open_run(root, evidence) as opened:
        served = opened.answer(_question(opened))
        after = opened.answer(_question(opened, no_such_parameter=1))
        assert isinstance(served, ServedProduct) and isinstance(after, RefusalEnvelope)
        addresses = [_address(opened, served), _address(opened, after), _address(opened, _early_refusal(opened))]

    # No source variable at all: the default opening refuses (unchanged), this one does not.
    with _open_run(root, evidence, environ={}, read_sources=False, acquire=_SourcesUnavailable()) as auditor:
        assert auditor.reads_sources is False
        for address in addresses:
            status, printed = _run(auditor, "replay", address)
            assert status == verbs.ANSWERED and printed.startswith("REPRODUCED:"), printed
            assert _run(auditor, "why", address)[0] == verbs.ANSWERED


def test_an_opening_without_source_settings_answers_nothing_and_writes_nothing(tmp_path: pathlib.Path) -> None:
    from ccf.products.product import SourcesNotRead

    root, evidence = _write_tree(tmp_path / "again"), tmp_path / "again" / "evidence-root"
    with _open_run(root, evidence, environ={}, read_sources=False) as auditor:
        before = _held(evidence)
        with pytest.raises(SourcesNotRead):
            auditor.answer(_question(auditor))
        with pytest.raises(SourcesNotRead):
            auditor.resolve(
                tenant=auditor.tenant_id, product_class="no.such-class", version="1.0.0",
                perspective=auditor.default_perspective, request=_question(auditor),
            )
        with pytest.raises(SourcesNotRead):
            auditor.sources  # noqa: B018
        assert _held(evidence) == before, "a refused question minted, marked or recorded nothing"
        assert auditor.evidence.incomplete() == []


def test_the_default_opening_still_requires_every_source_setting(tmp_path: pathlib.Path) -> None:
    from ccf.deployment.environment import EnvironmentMissing

    root = _write_tree(tmp_path)
    with pytest.raises(EnvironmentMissing):
        _open_run(root, tmp_path / "evidence-root", environ={})
