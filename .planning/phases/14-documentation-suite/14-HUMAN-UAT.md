---
status: partial
phase: 14-documentation-suite
source: [14-VERIFICATION.md]
started: 2026-08-03T19:32:00Z
updated: 2026-08-03T19:32:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Read the adopter's guide end to end as a first-time adopter

Read `public/tutorial/adopters-guide.md` from top to bottom as someone who has never seen
CCF. Follow it literally, starting from `pip install -e ".[dev]"` and continuing through the
replay section.

expected: Each section's prose explains WHY before the included snippet shows HOW; no step
assumes knowledge introduced only in a later section; the reader can reach a governed,
replayable deployment without consulting `docs/` or the source tree.
result: [pending]

### 2. Confirm the Mermaid diagrams render in a browser

Run `make docs-serve` and page through Concepts → Pillars.

expected: All five pillar diagrams plus the two seam and four sequence diagrams render as
visual Mermaid graphs rather than raw code blocks or empty figures; labels are legible and
edges resolve.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
