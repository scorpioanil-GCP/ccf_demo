---
phase: 3
reviewers: [gemini, ollama, codex, cursor]
reviewers_failed: [claude (skipped — self)]
gemini_note: first run stalled (agent-mode tool flailing, no file access); succeeded via stdin prompt
codex_note: first run failed (sandbox could not read prompt file); succeeded via stdin prompt after CODEX_API_KEY login
cursor_note: first run failed (directory trust prompt); succeeded with -f flag and CURSOR_API_KEY
reviewed_at: 2026-07-25
scope: Phase F deliverables (docs/FEASIBILITY.md, docs/ROADMAP.md) reviewed against CLAUDE.md §3.1 Phase F verification criteria
---

# Cross-AI Review — Phase 3 (Phase F — Feasibility & Scoping)

All four reviewers were given the full text of `docs/FEASIBILITY.md` and `docs/ROADMAP.md` plus the four CLAUDE.md §3.1 Phase F verification criteria: (1) every design component carries a verdict; (2) the v0.1 surface is explicit; (3) the 12-member Phase I gate list is checked against actual resolution status; (4) the test strategy names how each CI-enforced invariant is verified. Reviewers were instructed to rate HIGH only for a criterion violation, and to verify the LangGraph staging note is a recommendation, not a scope change.

## Gemini Review

### Summary
The Phase F deliverables are comprehensive, rigorously structured, and fully compliant with the CLAUDE.md §3.1 verification criteria. All 50 design components have valid implementation verdicts (47 strong fit, 3 out of scope) without triggering new design gaps. The roadmap establishes a clear v0.1 MVP surface anchored by in-process fabric examples and a viable path to Phase I.

### Strengths
- **Exhaustive traceability:** Appendix A maps all 126 inventory entries to component verdicts — zero coverage gaps.
- **Structural invariant enforcement:** §11 provides concrete, tool-specific verification mechanisms (AST lints, boot checks, property tests) for every CI-enforced invariant.
- **Risk realism:** high-risk clustering around external dependencies (LangGraph, ADK, A2A, MCP) with explicit containment (typed-HTTP fallback for A2A).
- **Decision integrity:** the 12 Phase I gates explicitly verified RESOLVED in §12.

### Concerns
- **High dependency risk (MEDIUM):** four high-risk components cluster in Milestone I.3; three harness adapters co-evolving against shifting vendor SDKs is significant integration pressure.
- **CINV-01 calibration (LOW):** prompt-shaped-literal lint needs false-positive tuning — friction point, not a design gap.

### Suggestions
- Provide standard fixture artifacts in I.1 boilerplate to unblock testing under the No-Hardcoding Rule.
- Exercise the `WireProtocol` typed-HTTP fallback in CI alongside the emergent A2A standard.

### Risk Assessment: MEDIUM (implementation), gate verdict **PASSED** — "All verification criteria from CLAUDE.md §3.1 are satisfied."

---

## Ollama Review (gpt-oss:120b-cloud)

### Summary
Both deliverables satisfy every clause of the §3.1 Phase F criteria: all 50 components carry one unambiguous verdict; the v0.1 surface is explicit in ROADMAP.md §2; the 12 gating decisions are listed RESOLVED in FEASIBILITY.md §12 and cross-checked against DECISIONS.md; the §11 test-strategy table enumerates a verification method for every CI-enforced invariant. The three-harness ruling is presented only as a recommendation; no per-component effort estimates appear (D-03 honored).

### Strengths
- Full component coverage — census matches 47/0/3.
- Explicit example-driven v0.1 surface.
- Gate-list verification with exact ruling identifiers, dates, approver.
- Comprehensive test strategy including the two new Phase F test classes (D-08, D-09), each tied to a CI job and pass criterion.
- Out-of-scope items tied to rulings and listed in the deferral register.
- Safe phrasing of the three-harness recommendation ("not a scope change") in both documents.

### Concerns
| # | Concern | Severity |
|---|---------|----------|
| 1 | High-risk external dependencies (MCP client, A2A, ADK, LangGraph) all in I.3 — could jeopardize the Phase I gate if unmitigated | MEDIUM (no criterion violation) |
| 2 | Shipped-operator set not enumerated for the composition-preservation harness | LOW |
| 3 | Exact mypy rule for the single-writer static gate not spelled out | LOW |
| 4 | LangGraph recommendation could use a clarifying footnote that D-IMPL-24 is unaltered | LOW |
| 5 | No effort estimates (D-03-compliant, but a delivery-predictability note) | LOW |

### Suggestions
- Add an explicit operator inventory for the composition-preservation harness.
- Document the mypy rule for the single-writer static gate in CI config.
- Add a risk-mitigation snapshot for the four high-risk adapters (version pinning, frozen conformance suite).

### Risk Assessment: LOW — "Ready to pass."

---

## Codex Review

### Summary
Phase F appears gate-ready. The deliverables satisfy the four minimum review criteria.

### Strengths
- Each component has a clear Verdict, rationale, and risk note; census 50 / 47 / 0 / 3.
- v0.1 surface explicit and example-driven (ROADMAP §2).
- All 12 Phase I gate decisions checked RESOLVED (§12).
- §11 covers the required CI invariants with concrete mechanisms, jobs, and pass criteria.
- LangGraph treatment correctly framed as intra-I.3 staging recommendation; ROADMAP §3 states no harness adapter is deferred.
- Appendix B dispositions all 7 carried advisories.

### Concerns
- **LOW — Decision-status evidence asserted, not deeply anchored:** §12 "DECISIONS.md ref" column repeats generic status-note wording rather than precise anchors.
- **LOW — Internal reference drift:** FEASIBILITY §3 operator-algebra rationale said "§9 test-strategy rows, added in a later plan," while the strategy lives in §11.
- **LOW — Appendix A INV-CH8-24 mapping:** maps via §6.4 to "MCP egress server" while §6.4 is also the Conversational Reporting deferral home — worth a consistency check.

### Suggestions
- Replace generic §12 refs with exact anchors; update the stale §9 reference to §11; spot-check INV-CH8-24; keep LangGraph text in its current posture.

### Risk Assessment: LOW — "Phase F is ready for D-GATE-F."

---

## Cursor Review

### Summary
Phase F deliverables satisfy all four §3.1 verification criteria. The LangGraph note is correctly framed as intra-I.3 sequencing advice, not a D-IMPL-24 scope change. Gate readiness: ready for Dave at D-GATE-F.

### Strengths
- Verdict completeness: 50 components, census 47/0/3 matches the body.
- Traceability: 126/126 rows mapped, including ruled deferrals for INV-CH8-19 and INV-CH8-21.
- v0.1 surface concrete, IdentityProvider explicitly out of v0.1 with a clear boundary vs full v0.
- Phase I gate check: all twelve gating IDs RESOLVED; non-gating D-IMPL-10 called out correctly.
- Test strategy covers all CINV-01..04 targets, single-writer static + boot, composition-preservation, and the three gates by canonical name; D-08/D-09 rows close Phase D advisories 2–3.
- D-IMPL-24 discipline held; advisory closure 7/7; D-03 honored.

### Concerns
- **MEDIUM — Feasibility optimism vs high-risk cluster:** zero `needs design choice` is criterion-compliant, but four high components in §9 sit on emergent 2026 surfaces; raises mini-cycle probability in I.3. Dave should treat the LangGraph staging recommendation as load-bearing risk management.
- **MEDIUM — Appendix A completeness asserted, not evidenced in-document:** the empty unique-key diff is claimed but not shown; INV-CH7 numbering jumps could read as missing rows.
- **LOW — ROADMAP §4 stale cross-ref:** says the test-strategy table is "added by the Phase F plan following this one" while §11 already contains it.
- **LOW — INV-CH8-24 section pointer:** easy to misread as mixing deferred and in-scope surfaces.

### Suggestions
- Attach the mechanical key-diff evidence next to Appendix A; get an explicit yes/no from Dave on the LangGraph staging note; fix the ROADMAP §4 stale reference; annotate the INV-CH7 numbering gaps.

### Risk Assessment: MEDIUM overall implementation risk; **LOW Phase F gate-criteria risk** — "gate-ready for presentation to Dave under CLAUDE.md §3.1."

---

## Consensus Summary (4 reviewers: Gemini, Ollama gpt-oss:120b, Codex, Cursor)

### Agreed strengths (all four)
- All four §3.1 Phase F criteria satisfied: 50/50 verdicts (census 47/0/3), explicit example-driven v0.1 surface, 12/12 gate list RESOLVED, per-invariant test strategy covering every CI-enforced invariant including the new D-08/D-09 test classes.
- LangGraph staging note correctly phrased as a recommendation for Dave, never a scope change; D-IMPL-24 preserved; no harness adapter deferred.
- Advisory Disposition appendix closes all 7 Phase D carried findings; D-03 (no effort estimates) honored.
- **Zero HIGH findings from any reviewer against the §3.1 criteria.**

### Net triage for the 03-04 gate

**Blocking:** none against the §3.1 criteria. Three doc-consistency findings were treated as blocking-lite and **fixed in-phase before presentation** (Phase 2 precedent):

| ID | Finding (source) | Fix |
|----|------------------|-----|
| B1 | Stale "§9 test-strategy rows, added in a later plan" in FEASIBILITY §3 (Codex LOW) | Retargeted to §11 in-place |
| B2 | Stale ROADMAP §4 "added by the Phase F plan following this one" (Cursor LOW) | Retargeted to FEASIBILITY §11 in-place |
| B3 | Appendix A key-diff asserted not evidenced + INV-CH7 numbering-gap ambiguity + INV-CH8-24 mapping ambiguity (Cursor MEDIUM / Codex LOW) | Appendix A preamble now records the re-verified 126/126 empty key-diff, notes that keys INV-CH7-34..39 and INV-CH7-69 do not exist in the inventory at source, and states why the MCP egress server component owns INV-CH8-24 (coexistence boundary; the §6.4 deferral entry is INV-CH8-21) |

Mechanical re-verification at this gate: 126 unique `INV-CHx-NN` keys extracted from `docs/SPEC_INVENTORY.md` and from FEASIBILITY.md Appendix A; `diff` empty.

**Advisory (recorded here, carried to Phase I planning):**
1. **I.3 high-risk cluster** (Gemini MEDIUM / Cursor MEDIUM / Ollama MEDIUM) — inherent to the ruled scope, already surfaced as the LangGraph staging recommendation for Dave at this gate. Phase I.3 planning should treat the staging recommendation as load-bearing risk management and pin vendor SDK versions at module boundaries.
2. **Operator inventory enumeration** (Ollama LOW) — freeze the shipped-operator list early in I.1 so the composition-preservation harness has a fixed target.
3. **Mypy rule documentation for the single-writer static gate** (Ollama LOW) — document the exact rule in CI configuration during I.1.
4. **§12 DECISIONS.md anchors** (Codex LOW) — generic status-note refs acceptable for the gate; precise anchors are optional polish.
5. **Fixture artifacts early** (Gemini suggestion) — ship fixture definition artifacts in I.1 boilerplate.
6. **A2A typed-HTTP fallback in CI** (Gemini suggestion) — exercise the fallback transport in CI during I.3.
7. **CINV-01 lint calibration** (Gemini LOW) — false-positive tuning is Phase I calibration, already noted in FEASIBILITY §10.

### Overall verdicts
- Gemini: PASSED — all §3.1 criteria satisfied.
- Ollama: LOW — ready to pass.
- Codex: LOW — ready for D-GATE-F.
- Cursor: LOW gate-criteria risk — gate-ready; approval remains Dave's alone.

**Net: Phase F self-review passes with zero blocking findings outstanding (B1–B3 fixed in-phase); 7 advisories carried to Phase I. Awaiting Dave's D-GATE-F ruling, including his decision on the LangGraph intra-I.3 staging recommendation (D-10).**
