"""The ApprovalSink test double — /tests fixtures only, never ships (D-09).

A scripted sink: it approves or rejects exactly as constructed, records every
grant it was asked to decide, and supplies an approver id string only —
approver *identity binding* is D-IMPL-21 and lands with I.4's real
ApprovalGate sink, which joins the conformance parametrization in
``tests/conformance/test_approval_sink.py`` with zero state-machine change
(D-09; T-05-19 accepted for I.2).

Lives in test fixtures rather than ``/src`` because a scripted approver is
test material, not mechanism: the SDK ships the Protocol and the state
machine, never a decision-maker.
"""

from __future__ import annotations

from ccf.skills.grants import ApprovalOutcome, SkillGrant


class ScriptedApprovalSink:
    """Decides every grant the same way, and remembers what it decided.

    Args:
        approve: The verdict this sink returns for every grant.
        approver_id: The id string recorded on every outcome. A fixture
            value — the SDK never synthesizes an identity.
    """

    def __init__(self, *, approve: bool, approver_id: str) -> None:
        self._approve = approve
        self._approver_id = approver_id
        self.decided: list[SkillGrant] = []

    def decide(self, grant: SkillGrant) -> ApprovalOutcome:
        """Record ``grant`` and return the scripted outcome."""
        self.decided.append(grant)
        return ApprovalOutcome(approved=self._approve, approver_id=self._approver_id)
