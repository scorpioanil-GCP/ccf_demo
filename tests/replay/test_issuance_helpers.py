"""The modulo-the-issuance comparison, watched failing before any green is trusted.

``tests/issuance.py`` states Dave's E1 (a) (``D-IMPL-378``, 2026-10-08 12:29 MST)
once, and thirteen restated tests across products, replay, MCP and the
conformance suite lean on it. A helper that passed everything would keep all of
them green forever, so each claim is planted here, one at a time, into a real
record — the committed golden ``13bd250`` record, read and never written — and
the helper is required to name it:

* a record with no issuance, or a malformed one, is not issued;
* two answers sharing one issuance are not issued apart;
* a difference in any member but the issuance is a different determination;
* a difference in the issuance alone is the same determination;
* a reference whose name and version are not both the record's own content
  address does not name that record.

Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from ccf.contracts.canonical import content_hash
from ccf.replay.record import NO_ISSUANCE, DecisionReplayRecord, new_issuance

from tests.issuance import (
    assert_issued,
    assert_named_by_its_own_content,
    assert_one_determination_issued_twice,
    differences_modulo_issuance,
    modulo_issuance,
)

#: The golden record's own directory and content address (its manifest names
#: the address; ``tests/replay/test_golden_13bd250.py`` holds the bytes to it).
GOLDEN = Path(__file__).parent / "fixtures" / "golden_13bd250" / "artifacts"
GOLDEN_ADDRESS = "401bfc181108a613c8bf2e08ced35bee9a96a0a18f2426a49881e94876affadc"

#: A fixture tenant and class for the references built below.
TENANT = "tenant-issuance-fixture"
RECORD_CLASS = "fixture.issuance-record"


def _golden() -> DecisionReplayRecord:
    record = DecisionReplayRecord.model_validate_json((GOLDEN / GOLDEN_ADDRESS).read_bytes())
    assert content_hash(record) == GOLDEN_ADDRESS, "the golden record moved"
    return record


def _issued(record: DecisionReplayRecord, issuance: str) -> DecisionReplayRecord:
    path = record.content_generation_path.model_copy(update={"issuance": issuance})
    return record.model_copy(update={"content_generation_path": path})


def _reference(name: str, version: str) -> str:
    return f"ccf-artifact://{TENANT}/{RECORD_CLASS}/{name}@{version}"


def test_an_unissued_or_malformed_issuance_is_not_issued() -> None:
    golden = _golden()
    assert golden.content_generation_path.issuance == NO_ISSUANCE
    with pytest.raises(AssertionError, match="issued per answer"):
        assert_issued(golden, what="golden, as filed")
    with pytest.raises(AssertionError, match="issued per answer"):
        assert_issued(_issued(golden, "A" * 64), what="upper-case")
    assert_issued(_issued(golden, new_issuance()), what="minted")


def test_two_answers_issued_apart_are_one_determination() -> None:
    golden = _golden()
    a, b = _issued(golden, new_issuance()), _issued(golden, new_issuance())
    assert differences_modulo_issuance(a, b) == []
    assert modulo_issuance(a) == modulo_issuance(b) == golden
    assert_one_determination_issued_twice(a, b, what="issued apart")


def test_one_shared_issuance_is_refused() -> None:
    a = _issued(_golden(), new_issuance())
    with pytest.raises(AssertionError, match="ONE issuance"):
        assert_one_determination_issued_twice(a, a, what="shared")


def test_an_unissued_side_is_refused() -> None:
    golden = _golden()
    with pytest.raises(AssertionError, match="issued per answer"):
        assert_one_determination_issued_twice(
            _issued(golden, new_issuance()), golden, what="one unissued"
        )


@pytest.mark.parametrize("member", ["content_generation_path", "tenant_id", "recorded_at"])
def test_any_other_difference_is_another_determination(member: str) -> None:
    golden = _golden()
    a, b = _issued(golden, new_issuance()), _issued(golden, new_issuance())
    if member == "content_generation_path":
        b = b.model_copy(
            update={
                "content_generation_path": b.content_generation_path.model_copy(
                    update={"plan_id": "a-plan-nobody-ran"}
                )
            }
        )
    elif member == "tenant_id":
        b = b.model_copy(update={"tenant_id": "another-tenant"})
    else:
        b = b.model_copy(update={"recorded_at": b.recorded_at + timedelta(seconds=1)})
    assert differences_modulo_issuance(a, b) == [member]
    with pytest.raises(AssertionError, match=member):
        assert_one_determination_issued_twice(a, b, what=f"planted {member}")


def test_a_reference_names_exactly_its_own_content() -> None:
    record = _issued(_golden(), new_issuance())
    address = content_hash(record)
    assert_named_by_its_own_content(_reference(address, address), record, what="own")
    other = content_hash(_golden())
    with pytest.raises(AssertionError, match="own content address"):
        assert_named_by_its_own_content(_reference(other, address), record, what="name moved")
    with pytest.raises(AssertionError, match="own content address"):
        assert_named_by_its_own_content(_reference(address, other), record, what="version moved")
    with pytest.raises(AssertionError, match="own content address"):
        assert_named_by_its_own_content(_reference(other, other), record, what="another record's")
