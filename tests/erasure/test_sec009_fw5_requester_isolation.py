"""FW-5 (round-5 re-review S5b): a SEC-009 control isolating "an eligible approver who is also the requester" (`D-IMPL-374` (4)).

Fix round 4's ruling 2 refuses an erasure approved by its own requester, and the
consult applies it twice over the requester the erasure DOOR signed: its own
explicit check (``approver-is-requester``) and the transport's eligibility rule,
whose requester clause is unconditional (``ccf.hitl.transport.check_approver_eligibility``).
The round-5 re-review measured a coverage gap: every SEC-009 self-approval test
used an approver who was NOT eligible, so membership refused her before either
requester clause ran — with both requester clauses severed (S5b) all SEC-009
tests stayed green while the b1 control read SUPPORTED, and only a SEC-006
transport test went red.

This control isolates the rule: bob IS an eligible erasure officer, the record
is genuinely door-signed, and the requester the door signed is bob himself.
"""

from __future__ import annotations

from pathlib import Path

from tests.erasure import harness as h
from tests.erasure import signing
from tests.erasure.test_sec009_fix5_rulings import _consult, _judgment, _outcome, _pin, _plant


def test_fw5_an_eligible_approver_who_is_the_requester_is_refused_as_the_requester(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    request = h.request(plane)
    address = _plant(
        plane, request, approver=h.APPROVER, approver_keys=signing.key_dir(), policy_ref=_pin(plane),
        requested_by=h.APPROVER, cap_principal=h.APPROVER,  # door=None: the GENUINE door key signs
    )
    # Named by the consult's own rule — never by membership, which bob passes.
    assert _judgment(plane, address) == "approver-is-requester"
    # And the address is withheld as index-unsupported, never SUPPORTED.
    assert _outcome(_consult(plane), address) == "unsupported(index-unsupported)"


def test_fw5_control_the_same_record_with_another_requester_is_supported(tmp_path: Path) -> None:
    """Sensitivity: only the requester differs from a record the consult supports."""
    plane = h.compose(tmp_path)
    request = h.request(plane)
    address = _plant(
        plane, request, approver=h.APPROVER, approver_keys=signing.key_dir(), policy_ref=_pin(plane),
        requested_by=h.REQUESTER, cap_principal=h.REQUESTER,
    )
    assert _judgment(plane, address) == "supported"
