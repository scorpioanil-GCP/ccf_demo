# 380-05 (fifth round, ruling 2 (a)) — the skill-grant ledger hands the approval sink a deep copy and keeps and saves its own grant

`D-IMPL-380`, the dated amendment of 2026-10-10 12:57 MST, Dave, verbatim: *"Copy before the approver is handed the
grant. An approver that rewrites the ledger's own object leaves a grant in effect whose saved bytes do not match its
id. That is the same hole, one handoff later."* *"The ledger keeps its own copy"* *"has to be true of the object the
approver receives."* And at 13:24 MST: *"The approver receives `grant.model_copy(deep=True)`. The ledger keeps and
saves its own grant."* Built in lane `380e-repair`, red test first. **SEC-020 stays OPEN**; nothing here changes a SEC
row. The fifth round's two words-only items (the HITL stall sentence, and `revoke` and `state` named among the readers
of saved data) amend fragment `380-04` in place.

**What the test measures, on test fixtures.** `tests/skills/test_grant_approval_sink_holds_a_copy.py` (1 case, red on
`80169f85`): under a regime whose grants require approval, an approval sink that rewrote the `skill_name` of the grant
it received and approved left (i) the saved `effective` record's grant hashing to something other than its record id,
(ii) the `grant_effective` audit `version` naming the rewrite, and (iii) the caller's own grant rewritten. Now all
three are the grant as built.

## ccf.skills.grants.GrantLedger

- Surface: ccf.skills.grants.GrantLedger
- Public surface: true
- Change type: behavior
- Before: on the approval path the ledger handed the approval sink its own `SkillGrant` (`self._sink.decide(grant)`), and wrote the `effective` record and its `grant_effective` audit event from that same object, so a sink that rewrote the grant it received left a grant in effect whose saved bytes do not hash to its record id, and rewrote the caller's object.
- After: the approval sink receives `grant.model_copy(deep=True)`; the ledger keeps its own grant and writes every later state, and its audit event, from it, so the `effective` record is saved as built, under the record id the grant as built hashes to.
- Why: `D-IMPL-380` fifth round, ruling 2 (a), 2026-10-10 12:57 MST. The builder's finding B-2 and the Fable seat's finding F-1 on the fourth-round delta review, reproduced by the coordinator at `197f5b4f`. Red test: `tests/skills/test_grant_approval_sink_holds_a_copy.py`.
- Migration: none for an approval sink that does not change what it is handed. A sink that relied on altering the grant it receives no longer reaches the ledger's grant.

## ccf.skills.GrantLedger

- Surface: ccf.skills.GrantLedger
- Public surface: true
- Change type: behavior
- Before: as for `ccf.skills.grants.GrantLedger`
- After: as for `ccf.skills.grants.GrantLedger`
- Why: as for `ccf.skills.grants.GrantLedger`
- Migration: as for `ccf.skills.grants.GrantLedger`
