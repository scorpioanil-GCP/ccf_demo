# Phase 13: Examples Suite Upgrade - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-02
**Phase:** 13-examples-suite-upgrade
**Areas discussed:** README narration format, Scenario enrichment strategy, Expected-output churn policy, Adaptation guidance format

---

## README narration format

| Option | Description | Selected |
|--------|-------------|----------|
| Rich README only | One narrated README per example; Phase 14 mounts directly | ✓ |
| README + walkthrough doc each | Short README + docs/walkthrough-NN.md per example | |
| README + one suite guide | Per-example READMEs + a single progressive suite guide | |

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed template, all 8 | Identical section order everywhere; lintable | ✓ |
| Template + per-example freedom | Mandatory core, optional extra sections | |

| Option | Description | Selected |
|--------|-------------|----------|
| Path refs + tiny excerpts | ≤8-line excerpts, no include machinery | ✓ |
| Literal includes (--8<--) | Zero drift but raw markers on GitHub | |
| Full pasted snippets | Self-contained but high drift risk | |

| Option | Description | Selected |
|--------|-------------|----------|
| Engineer new to CCF | Gloss every CCF term on first use w/ whitepaper link | ✓ |
| CCF-primed reader | Assume quickstart+walkthrough done | |
| Layered: 00 teaches, later links back | 00 carries glossary; 01–07 back-reference | |

**Notes:** Audience decision motivated by the Phase 12 UAT observation
(unexplained "CI" jargon).

---

## Scenario enrichment strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Keep current domains, deepen | No re-theming; diffs attributable to enrichment | ✓ |
| Re-theme for a designed mix | Curated domain spread; regenerates everything | |
| Banking thread + varied satellites | 00 banking, others varied | |

| Option (multiSelect) | Selected |
|--------|----------|
| All six specialization axes | ✓ |
| Half-life decay + context debt | |
| Temporal operators + T axis | |
| HITL variants beyond ApprovalGate | |

| Option | Description | Selected |
|--------|-------------|----------|
| Axes required, rest opportunistic | Planner places other surfaces where natural | ✓ |
| Axes only, defer the rest | | |
| Axes + half-life/debt required | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Artifacts-first, code frozen-ish | run.py changes only for new artifact fields | ✓ |
| Code may grow narration | 08-style banners everywhere | |

---

## Expected-output churn policy

| Option | Description | Selected |
|--------|-------------|----------|
| Per-example atomic commits | Enrichment + regenerated output in one commit | ✓ |
| Regen helper + manifest | Script + dated CHANGES manifest | |
| Two-commit ritual | Separate enrichment and regen commits | |

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, document per example | Regen command in each README + reviewed-event warning | ✓ |
| Yes, plus a make target | `make regen-example-NN` | |
| No, leave implicit | | |

---

## Adaptation guidance format

| Option | Description | Selected |
|--------|-------------|----------|
| README section + artifact comments | "Adapt it" section + header comments in artifacts | ✓ |
| README section only | | |
| Worked adaptation example | Before/after diffs per example | |

| Option | Description | Selected |
|--------|-------------|----------|
| README table + existing lints | "yours to edit vs mechanism" column; No-Hardcoding lint enforces | ✓ |
| Add a docs-consistency check | CI headings grep across 8 READMEs | |
| Manual review only | | |

---

## Claude's Discretion

- Which examples absorb the opportunistic SDK surfaces (half-life/debt, temporal, HITL variants)
- Wording/ordering within the fixed template; excerpt selection within the ≤8-line rule
- Optional light retrofit of example 08's README to the shared template

## Deferred Ideas

- Per-example walkthrough docs with literal includes → Phase 14 candidate
- `make regen-example-NN` targets → reconsider if churn becomes frequent
- Worked before/after adaptation diffs → Phase 14 flagship candidate
- README template-sections CI check → optional for planner, not required
