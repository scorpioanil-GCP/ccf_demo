# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The bank door's comparator and timing judge (``packaging/bank-controlled/door_checks.py``) — estate-free.

SEC-020 Parts 1-3 (Dave, 2026-10-16 21:32 GO; ``SEC-020-PARTS-1-3-BRIEF.md`` §3-§5). The comparator decides
whether an unknown facility and an existing one outside the requested scope got ONE answer, so its masking is the
place a defect could hide. These tests hold that it masks the three values it may, only after checking them, and
nothing else: every other field changed alone is a FAIL naming that field. They also hold that it never raises,
including on the two shapes measured through the bank door before the fix (a governed refusal against a runtime
failure). The timing judge is held to the rule ``question.yaml`` fixes: each half of it alone can fail a run.

The answer shapes below are the door's own, copied from the measurement of 2026-10-16
(``ccf_saves/2026-10-16-383/sec020-measure/raw/pair_a_full_bytes.json``), not invented.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
from typing import Any

import pytest
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
BANK = REPO_ROOT / "packaging" / "bank-controlled"


def _load_door_checks() -> Any:
    # By path: `packaging` is also the name of a PyPI distribution, which an import would resolve to instead.
    spec = importlib.util.spec_from_file_location("door_checks", BANK / "door_checks.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["door_checks"] = module
    spec.loader.exec_module(module)
    return module


dc = _load_door_checks()

W, A = "FAC-5B8418", "FAC-01A702"
DIGEST_W, DIGEST_A = "a" * 64, "b" * 64
TENANT = "cp-06-canonical-demo"


def _refusal_text(facility: str, digest: str, **change: Any) -> str:
    """A post-fix refusal in the door's own key order (`isError` false, kind `subject-unavailable`)."""
    reference = f"ccf-artifact://{TENANT}/ccf.replay-record/{digest}@{digest}"
    envelope: dict[str, Any] = {
        "answered": {"asked_at": "2026-09-07T12:00:00.000000Z", "freshness": "as-filed",
                     "intent": "lgd-assessment", "subject": facility},
        "content_address": None,
        "producer": {"producer_id": "cp-06-canonical-collateral-and-setoff-coverage-egress", "tenant_id": TENANT},
        "product_json": None,
        "refusal": {
            "detail": "the requested subject is not available to this principal under this product",
            "disclosure": "minimal",
            "fields": {"cause": '"undisclosed"', "error_code": '"undisclosed"'},
            "key": None, "kind": "subject-unavailable", "pre_assembly_lineage": None,
            "reason": "subject-unavailable", "replay_reference": reference,
            "request": {"parameters": {"borrower_scope": ["529900E95812SYWMCE44"], "facility_id": facility},
                        "product_id": "credit-risk.collateral-coverage", "product_version": "1.0.0",
                        "temporal_boundary": "2026-09-07T12:00:00.000000Z"},
        },
        "replay_ref": reference,
        "request": {"parameters": {"borrower_scope": ["529900E95812SYWMCE44"], "facility_id": facility},
                    "product_id": "credit-risk.collateral-coverage",
                    "temporal_boundary": "2026-09-07T12:00:00.000000Z"},
    }
    for dotted, value in change.items():
        *path, last = dotted.split("__")
        target = envelope
        for key in path:
            target = target[key]
        if value is _DELETE:
            del target[last]
        else:
            target[last] = value
    return json.dumps(envelope, separators=(",", ":"))


_DELETE = object()


def _tool(facility: str, text: str, *, is_error: bool = False, structured: bool = True) -> Any:
    result = {"meta": None, "content": [{"type": "text", "text": text, "annotations": None, "meta": None}],
              "structuredContent": {"result": text} if structured else None, "isError": is_error}
    return dc.Answer("tool", facility, result)


def _template(facility: str, text: str, address: str | None = None) -> Any:
    address = address or f"ccf-product://{TENANT}/credit-risk.collateral-coverage/1.0.0/q/{facility}-question"
    result = {"meta": None, "contents": [{"uri": address, "mimeType": "application/json", "meta": None, "text": text}]}
    return dc.Answer("template", facility, result, None, address)


def _pair(**change: Any) -> tuple[Any, Any]:
    return _tool(W, _refusal_text(W, DIGEST_W)), _tool(A, _refusal_text(A, DIGEST_A, **change))


# --- what may be masked, and nothing else --------------------------------------------------------------------------


def test_two_answers_that_differ_only_in_the_masked_values_compare_equal() -> None:
    outside, unknown = _pair()
    assert dc.compare(outside, unknown).ok
    assert dc.signature(outside) == dc.signature(unknown)
    assert dc.compare(_template(W, _refusal_text(W, DIGEST_W)), _template(A, _refusal_text(A, DIGEST_A))).ok


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"refusal__kind": "ttl-anchor-refusal"}, "refusal.kind"),
        ({"refusal__reason": "ttl-anchor-unresolvable"}, "refusal.reason"),
        ({"refusal__detail": "the requested subject does not exist"}, "refusal.detail"),
        ({"refusal__disclosure": "reasoned"}, "refusal.disclosure"),
        ({"refusal__key": "k"}, "refusal.key"),
        ({"refusal__fields": {"cause": '"nonexistent"', "error_code": '"undisclosed"'}}, "refusal.fields.cause"),
        ({"refusal__fields": {"cause": '"undisclosed"', "error_code": '"facility-not-held"'}}, "refusal.fields.error_code"),
        ({"refusal__fields": {"cause": '"undisclosed"'}}, "refusal.fields (keys"),
        ({"refusal__policy_bindings": []}, "refusal (keys"),
        ({"refusal__pre_assembly_lineage": {"operators": []}}, "refusal.pre_assembly_lineage"),
        ({"content_address": "c" * 64}, "text.content_address"),
        ({"product_json": "{}"}, "text.product_json"),
        ({"producer__tenant_id": "another-tenant"}, "text.producer.tenant_id"),
        ({"request__product_id": "credit-risk.other"}, "text.request.product_id"),
        ({"refusal__request__product_version": "1.1.0"}, "refusal.request.product_version"),
        ({"request__temporal_boundary": "2026-09-08T12:00:00.000000Z"}, "text.request.temporal_boundary"),
        ({"answered__intent": "annual-review"}, "text.answered.intent"),
        ({"answered__freshness": "standard"}, "text.answered.freshness"),
        ({"answered__asked_at": "2026-09-08T12:00:00.000000Z"}, "text.answered.asked_at"),
        ({"request__parameters__borrower_scope": ["ANOTHER"]}, "text.request.parameters.borrower_scope"),
    ],
)
def test_any_other_field_changed_alone_is_a_fail_naming_that_field(change: dict[str, Any], field: str) -> None:
    verdict = dc.compare(*_pair(**change))
    assert not verdict.ok, verdict
    assert field in (verdict.field or ""), verdict


def test_reordered_keys_are_a_fail() -> None:
    outside = _tool(W, _refusal_text(W, DIGEST_W))
    envelope = json.loads(_refusal_text(A, DIGEST_A))
    reordered = json.dumps(dict(reversed(list(envelope.items()))), separators=(",", ":"))
    verdict = dc.compare(outside, _tool(A, reordered))
    assert not verdict.ok and "keys" in (verdict.field or ""), verdict


def test_a_missing_replay_reference_on_one_side_is_a_fail() -> None:
    verdict = dc.compare(*_pair(replay_ref=_DELETE))
    assert not verdict.ok and "replay reference" in (verdict.field or ""), verdict


def test_the_asked_id_appearing_anywhere_but_its_three_echoes_is_a_fail() -> None:
    leaked = "the requested subject is not available to this principal under this product (" + A + ")"
    verdict = dc.compare(*_pair(refusal__detail=leaked))
    assert not verdict.ok and "facility id count" in (verdict.field or ""), verdict


def test_an_echo_that_is_not_the_asked_id_is_a_fail() -> None:
    verdict = dc.compare(*_pair(answered__subject="FAC-999999"))
    assert not verdict.ok and "answered.subject" in (verdict.field or ""), verdict


def test_the_two_copies_of_a_tool_answer_must_be_byte_equal() -> None:
    outside, unknown = _pair()
    altered = copy.deepcopy(dict(unknown.result))
    altered["structuredContent"] = {"result": altered["structuredContent"]["result"] + " "}
    verdict = dc.compare(outside, dc.Answer("tool", A, altered))
    assert not verdict.ok and "structuredContent" in (verdict.field or ""), verdict


@pytest.mark.parametrize(
    ("member", "value"),
    [("isError", True), ("meta", {"x": 1}), ("structuredContent", None)],
)
def test_the_result_outside_the_text_is_compared_whole(member: str, value: Any) -> None:
    outside, unknown = _pair()
    altered = copy.deepcopy(dict(unknown.result))
    altered[member] = value
    verdict = dc.compare(outside, dc.Answer("tool", A, altered))
    assert not verdict.ok, verdict


@pytest.mark.parametrize(("member", "value"), [("annotations", {"audience": ["user"]}), ("type", "resource")])
def test_a_content_item_is_compared_whole(member: str, value: Any) -> None:
    outside, unknown = _pair()
    altered = copy.deepcopy(dict(unknown.result))
    altered["content"][0][member] = value
    verdict = dc.compare(outside, dc.Answer("tool", A, altered))
    assert not verdict.ok, verdict


def test_text_length_alone_is_a_fail() -> None:
    outside, unknown = _pair()
    padded = unknown.text() + " "
    verdict = dc.compare(outside, _tool(A, padded))
    assert not verdict.ok, verdict


def test_a_governed_refusal_is_recognized_on_both_routes() -> None:
    """Added 2026-10-16 after the first post-fix run: the predicate required `isError: false`, which a template read
    never carries, so it called every template refusal "not governed" — and no test here had asked it about one."""
    assert dc.is_governed_refusal(_tool(W, _refusal_text(W, DIGEST_W)))
    assert dc.is_governed_refusal(_template(W, _refusal_text(W, DIGEST_W)))
    assert not dc.is_governed_refusal(dc.Answer("template", A, None, "McpError: ccf-runtime-failure:cfe4", "x"))
    assert not dc.is_governed_refusal(_tool(A, _refusal_text(A, DIGEST_A), is_error=True))
    assert not dc.is_governed_refusal(_template(A, _refusal_text(A, DIGEST_A, replay_ref=_DELETE)))


def test_the_template_route_masks_only_the_address_it_was_asked_for() -> None:
    outside = _template(W, _refusal_text(W, DIGEST_W))
    unknown = _template(A, _refusal_text(A, DIGEST_A))
    altered = copy.deepcopy(dict(unknown.result))
    altered["contents"][0]["uri"] = "ccf-product://elsewhere"
    assert not dc.compare(outside, dc.Answer("template", A, altered, None, unknown.address)).ok
    altered = copy.deepcopy(dict(unknown.result))
    altered["contents"][0]["mimeType"] = "text/plain"
    verdict = dc.compare(outside, dc.Answer("template", A, altered, None, unknown.address))
    assert not verdict.ok and "mimeType" in (verdict.field or ""), verdict


# --- today's measured shapes: a FAIL, never a raise ---------------------------------------------------------------

#: Measured 2026-10-16 through the bank door on 5a3e9b9f (`pair_a_full_bytes.json`): the out-of-scope answer...
MEASURED_OUT_OF_SCOPE = (
    '{"answered":{"asked_at":"2026-09-07T12:00:00.000000Z","freshness":"as-filed","intent":"lgd-assessment",'
    '"subject":"FAC-01BB3F"},"content_address":null,"producer":{"producer_id":'
    '"cp-06-canonical-collateral-and-setoff-coverage-egress","tenant_id":"cp-06-canonical-demo"},"product_json":null,'
    '"refusal":{"detail":"the product declares an evidence-anchored time-to-live and the evidence it rests on carries'
    ' no instant to anchor it on","disclosure":"minimal","fields":{"now":"\\"undisclosed\\"","observation_types":'
    '"\\"undisclosed\\"","ttl_anchor":"\\"undisclosed\\"","valid_from_rows":"\\"undisclosed\\""},"key":null,'
    '"kind":"ttl-anchor-refusal","policy_bindings":[{"identity":"cp-06-canonical-demo/request_contract","kind":'
    '"artifact","version":"b77e7663a8517e43f2aad5b00ffd0e3999a484218bf8ed12612fcc37569136cb"}],'
    '"pre_assembly_lineage":null,"reason":"ttl-anchor-unresolvable","replay_reference":'
    '"ccf-artifact://cp-06-canonical-demo/ccf.replay-record/c726ab550c146275c8038a3142de36560f691cc1d72571a08d50574773df4d00'
    '@c726ab550c146275c8038a3142de36560f691cc1d72571a08d50574773df4d00","request":{"parameters":{"borrower_scope":'
    '["2549001IGRCG4F0RLD36"],"facility_id":"FAC-01BB3F"},"product_id":"credit-risk.collateral-coverage",'
    '"product_version":"1.0.0","temporal_boundary":"2026-09-07T12:00:00.000000Z"}},"replay_ref":'
    '"ccf-artifact://cp-06-canonical-demo/ccf.replay-record/c726ab550c146275c8038a3142de36560f691cc1d72571a08d50574773df4d00'
    '@c726ab550c146275c8038a3142de36560f691cc1d72571a08d50574773df4d00","request":{"parameters":{"borrower_scope":'
    '["2549001IGRCG4F0RLD36"],"facility_id":"FAC-01BB3F"},"product_id":"credit-risk.collateral-coverage",'
    '"temporal_boundary":"2026-09-07T12:00:00.000000Z"}}'
)
#: ...and the unknown facility's (`isError` true, an opaque runtime-failure id, no structured content).
MEASURED_UNKNOWN = "Error executing tool request_context_product: ccf-runtime-failure:2d66a1d51cb04befbbd4637ab0707a14"


def test_the_measured_pre_fix_tool_pair_is_a_fail_at_iserror_without_raising() -> None:
    outside = _tool("FAC-01BB3F", MEASURED_OUT_OF_SCOPE)
    unknown = _tool(A, MEASURED_UNKNOWN, is_error=True, structured=False)
    verdict = dc.compare(outside, unknown)
    assert not verdict.ok and verdict.field == "tool: isError", verdict
    assert dc.signature(outside) != dc.signature(unknown)
    assert dc.is_governed_refusal(outside) and not dc.is_governed_refusal(unknown)


def test_the_measured_pre_fix_template_pair_is_a_fail_at_result_versus_error_without_raising() -> None:
    outside = _template("FAC-01BB3F", MEASURED_OUT_OF_SCOPE)
    unknown = dc.Answer("template", A, None, "McpError: Error creating resource from template: ccf-runtime-failure:cfe4",
                        "ccf-product://x")
    verdict = dc.compare(outside, unknown)
    assert not verdict.ok and "result-versus-error" in (verdict.field or ""), verdict


def test_two_runtime_failures_never_compare_equal() -> None:
    first = _tool(W, MEASURED_UNKNOWN, is_error=True, structured=False)
    second = _tool(A, MEASURED_UNKNOWN.replace("2d66", "9f00"), is_error=True, structured=False)
    assert not dc.compare(first, second).ok
    assert not dc.compare(first, first).ok, "an unmaskable answer is never a PASS, even against itself"


@pytest.mark.parametrize("garbage", [None, "not json", "[]", '{"refusal": 1}'])
def test_garbage_is_a_fail_and_never_a_raise(garbage: str | None) -> None:
    outside, _ = _pair()
    broken = dc.Answer("tool", A, {"content": [{"type": "text", "text": garbage}], "isError": False})
    assert not dc.compare(outside, broken).ok
    assert dc.signature(broken).startswith("unmaskable")


# --- the timing judge ----------------------------------------------------------------------------------------------

QUESTION = yaml.safe_load((BANK / "question.yaml").read_text(encoding="utf-8"))
RULE = dc.TimingRule.from_settings(QUESTION["timing"])


def test_the_timing_rule_is_the_one_fixed_before_the_remedy_ran() -> None:
    """The brief's §4, as `question.yaml` carries it. Loosening it is a ruling, and this test is where it shows."""
    assert (RULE.pairs, RULE.warmup_pairs, RULE.band, RULE.median_bound_ms) == (100, 2, (0.35, 0.65), 15.0)
    assert RULE.control_iqr_ceiling_ms == 58.0


def _symmetric(n: int = 100, shift: float = 0.0) -> list[float]:
    return [shift + (i % 21 - 10) * 3.0 for i in range(n)]


@pytest.mark.parametrize(
    ("differences", "passed"),
    [
        (_symmetric(), True),
        (_symmetric(shift=40.0), False),
        (_symmetric(shift=-40.0), False),
        ([-1.0] * 40 + [25.0] * 60, False),  # the proportion in the band, the median 25 ms
        ([-50.0] * 20 + [1.0] * 80, False),  # the median within 15 ms, the proportion 0.8
    ],
    ids=["no-difference", "plus-40", "minus-40", "median-25-only", "proportion-0.8-only"],
)
def test_the_judge_needs_both_halves_of_the_rule(differences: list[float], passed: bool) -> None:
    assert dc.judge_pairs(differences, RULE).passed is passed


def _rows(name: str, arms: tuple[str, str], differences: list[float], *, signature: str = "s") -> list[Any]:
    rows = []
    for index, d in enumerate(differences):
        rows.append(dc.TimingRow(name, index, arms[0], W, 200.0 + d, 0.0, signature))
        rows.append(dc.TimingRow(name, index, arms[1], A, 200.0, 0.0, signature))
    return rows


def test_a_failing_control_makes_the_run_invalid() -> None:
    rows = _rows("T0", ("first", "second"), _symmetric(shift=40.0)) + _rows("T1", ("existing", "unknown"), _symmetric())
    run = dc.judge_run(rows, RULE, control="T0", judged=["T1"])
    assert not run.valid and "control" in (run.why_invalid or "")
    assert run.judged["T1"].passed, "an INVALID run still reports the judged pair's own numbers"


def test_a_failed_call_makes_the_run_invalid() -> None:
    rows = _rows("T0", ("first", "second"), _symmetric()) + _rows("T1", ("existing", "unknown"), _symmetric())
    rows[-1].failure = "raised"
    assert not dc.judge_run(rows, RULE, control="T0", judged=["T1"]).valid


def test_a_pair_whose_answers_differ_is_a_part_one_failure() -> None:
    rows = _rows("T0", ("first", "second"), _symmetric()) + _rows("T1", ("existing", "unknown"), _symmetric())
    rows[-2].signature = "different"
    run = dc.judge_run(rows, RULE, control="T0", judged=["T1"])
    assert run.valid and run.judged["T1"].passed
    assert run.signature_mismatches == {"T1": [f"#{len(_symmetric()) - 1} {W} vs {A}"]}
