# 380-04 (fourth round, rulings 1 (a) and 2 (b)) — the skill-grant ledger hands the state store a deep copy and keeps its own grant; the HITL queue key is disclosed

`D-IMPL-380`, the dated amendment of 2026-10-10 10:58 MST, Dave, verbatim: *"The skill-grant ledger is the same hole.
Copy before the save. The approver sees the grant as built, not as the store rewrote it. The 09:18 principle already
covers it."* *"Record the HITL queue key. The approval binding is unaffected, and this round does not grow to every
handoff. Say what the caller can be told, and that the binding does not change."* And at 11:09 MST: *"yes the brief
matches the ruling - build it."* Built in lane `380d-repair`, red test first. **SEC-020 stays OPEN**; nothing here
changes a SEC row.

Fragment `380-03` made the workflow engine's Control Plane state writes hand the state store a deep copy. This fragment
applies the same rule to the skill-grant ledger's state writes, and records, in words only, what a HITL transport can
make the caller be told. The HITL handoff is not copied.

**What the test measures, on test fixtures.** `tests/skills/test_grant_state_store_holds_a_copy.py` (1 case, red on
`4d4f2dd1`): under a regime whose grants require approval, a state store that rewrote the `skill_name` of the grant
inside the record it was handed had its rewrite reach the approval sink, which decided on a grant other than the one
built, and reach the caller's own grant. Now the sink decides on the grant as built.

## ccf.skills.grants.GrantLedger

- Surface: ccf.skills.grants.GrantLedger
- Public surface: true
- Change type: behavior
- Before: every grant state write handed the Control Plane state store a `GrantStateRecord` built around the ledger's own `SkillGrant`, and on the approval path the ledger then handed that same grant to the approval sink, so a state store that rewrote the grant while holding it had its rewrite decided on by the approver, and carried by every later use of the grant in the same passage.
- After: the one function every grant state write uses (`_put_state`, the only `self._writer.write(` in the module) hands the state store a deep copy of the record taken before the save; the ledger keeps its own grant, so the approval sink and every later use in the same passage see the grant as built. The saved-bytes limit, state-store form: the state store saves its copy, and a later reader of the saved record (`bound_view`, `effective_hashes`, `revoke`, `state` and the folds) reads what the store saved. A revocation records the grant it read back: its write and its audit event name what the store saved (amended in the fifth round, ruling 3 (a), Dave 12:57 MST: *"Add revoke and state to the list of readers of saved data."*).
- Why: `D-IMPL-380` fourth round, ruling 1 (a), 2026-10-10 10:58 MST. Red test: `tests/skills/test_grant_state_store_holds_a_copy.py`.
- Migration: none for a state store that does not change what it is handed.

## ccf.skills.GrantLedger

- Surface: ccf.skills.GrantLedger
- Public surface: true
- Change type: behavior
- Before: as for `ccf.skills.grants.GrantLedger`
- After: as for `ccf.skills.grants.GrantLedger`
- Why: as for `ccf.skills.grants.GrantLedger`
- Migration: as for `ccf.skills.grants.GrantLedger`

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: the engine's docstrings did not say that the HITL transport is handed the engine's own pending event.
- After: unchanged behavior; amended in the fifth round, the docstrings of `_suspend` and `_restore_request`, and the security page, say: A HITL transport is handed the engine's own pending event, which is not copied. A transport that alters it can change the `event_key` the caller is told in `WorkflowSuspended`, and, because resume looks for the key it recomputes (`_event_key`) among the events the transport holds, a transport that alters the key can keep the gate from ever opening, and each recovery queues another request. Nothing is wrongly approved: the approval binding, the hash of the suspension record as built, does not change.
- Why: `D-IMPL-380` fourth round, ruling 2 (b), 2026-10-10 10:58 MST (the Fable seat's finding F-2 on the third-round delta review, reproduced by the coordinator at `06414dbd`); replaced in the fifth round, ruling 1 (a), 2026-10-10 12:57 MST: *"The current sentence understates it. Say that a queue which alters the key can keep the gate from ever opening, and that each recovery queues another request. Nothing is wrongly approved."* The builder's finding B-1 on the fourth-round delta review, reproduced by the coordinator at `197f5b4f` and re-measured by lane `380e-repair` before the sentence was written; the binding is the one `tests/workflow/test_state_store_holds_a_copy.py` holds to the record as built. The recovery code is not changed.
- Migration: none.
