# Copyright (c) 2026 David Castillo. All rights reserved.
"""Behavioral checks for the banking example; no mocks of SDK controls."""

import unittest

from ccf.agents.errors import SkillNotBound
from ccf.authz.capability import SkillGrant as SkillGrantAuthority
from ccf.contracts.canonical import content_hash
from ccf.skills.grants import ApprovalRejected
from ccf.skills.wire_arguments import ArgumentRefused

from calculation import calculate
from run import Demo, demonstrate


class BankingSkillsTests(unittest.TestCase):
    def test_end_to_end_results_and_audit(self):
        _, evidence = demonstrate()
        first, second = evidence["calculations"]
        self.assertEqual((first["leverage_headroom"], first["coverage_headroom"]), ("0.50", "1.00"))
        self.assertEqual(first["status"], "within-limits")
        self.assertEqual((second["leverage_headroom"], second["coverage_headroom"]), ("-0.50", "-0.50"))
        self.assertEqual(second["status"], "review-required")
        self.assertEqual(evidence["call_counts"], {"calculator": 2, "writeback": 0})
        self.assertEqual(evidence["writeback_refusal"]["excess_scopes"], ["covenant-writeback"])
        events = evidence["audit_events"]
        self.assertEqual([e["sequence"] for e in events], list(range(len(events))))
        self.assertEqual(
            [e["action"] for e in events if e["action"].startswith("grant_")],
            ["grant_requested", "grant_pending_approval", "grant_effective",
             "grant_requested", "grant_refused", "grant_revoked"],
        )
        effective = next(e for e in events if e["action"] == "grant_effective")
        self.assertEqual(effective["actor"], "scripted-demo-risk-officer")
        denies = [e for e in events if e["action"] == "authz_decision" and not e["resolved"]]
        self.assertEqual(len(denies), 1)
        self.assertEqual(denies[0]["actor"], "demo-credit-analyst")
        self.assertFalse(evidence["tool_surface"]["input_schema"]["additionalProperties"])

    def test_authorization_denial_does_not_request_a_grant(self):
        demo = Demo()
        with self.assertRaises(PermissionError):
            demo.request("calculator", identity="analyst")
        self.assertFalse(any(e.action.startswith("grant_") for e in demo.audit.events()))
        self.assertEqual(demo.sink.requests, [])

    def test_operator_scope_does_not_cover_another_agent(self):
        demo = Demo()
        with self.assertRaises(PermissionError):
            demo.authority(SkillGrantAuthority, "demo-bank/ccf.agent-definition/another-agent")

    def test_rejected_approval_leaves_skill_unbound(self):
        demo = Demo(approve=False)
        result = demo.request("calculator")
        self.assertIsInstance(result, ApprovalRejected)
        self.assertEqual(demo.ledger.state(content_hash(demo.grants["calculator"])), "refused")
        with self.assertRaises(SkillNotBound):
            demo.agent.invoke_skill(demo.entries["calculator"].name, arguments={"counterparty_id": "demo-manufacturer"})
        self.assertEqual(demo.calculator.calls, 0)

    def test_argument_schema_refuses_before_dispatch(self):
        demo = Demo()
        self.assertIsInstance(demo.request("calculator"), str)
        for arguments in ({}, {"counterparty_id": 12}, {"counterparty_id": "demo-manufacturer", "override": True}):
            with self.subTest(arguments=arguments), self.assertRaises(ArgumentRefused):
                demo.agent.invoke_skill(demo.entries["calculator"].name, arguments=arguments)
        self.assertEqual(demo.calculator.calls, 0)

    def test_unknown_counterparty_is_refused_by_business_callable(self):
        demo = Demo()
        self.assertIsInstance(demo.request("calculator"), str)
        with self.assertRaisesRegex(ValueError, "outside the demonstration portfolio"):
            demo.agent.invoke_skill(demo.entries["calculator"].name, arguments={"counterparty_id": "not-in-portfolio"})

    def test_threshold_equality_is_compliant(self):
        result = calculate(self.row())
        self.assertEqual(result["status"], "within-limits")
        self.assertEqual((result["leverage_headroom"], result["coverage_headroom"]), ("0.00", "0.00"))

    def test_rounding_does_not_hide_a_breach(self):
        result = calculate({**self.row(), "total_debt": "210.006", "interest_expense": "20.0001"})
        self.assertEqual((result["leverage"], result["interest_coverage"]), ("3.50", "3.00"))
        self.assertEqual((result["leverage_breach"], result["coverage_breach"]), ("true", "true"))

    def test_unsupported_financial_inputs_are_refused(self):
        for key, value in (("ebitda", "0"), ("interest_expense", "0"), ("ebitda", "-1"),
                           ("total_debt", "NaN"), ("interest_expense", "Infinity"), ("ebitda", 60)):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                calculate({**self.row(), key: value})

    @staticmethod
    def row():
        return {"total_debt": "210", "ebitda": "60", "interest_expense": "20",
                "maximum_leverage": "3.50", "minimum_interest_coverage": "3.00"}


if __name__ == "__main__":
    unittest.main()
