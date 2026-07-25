# Provisional Resolutions pending D-GATE-D confirmation

Consolidated register for the D-GATE-D presentation, per plan 02-04 Task 3 (CONTEXT specifics: required at the gate even when empty).

## Census evidence (2026-07-25)

- **49/49 marathon census: PASS.** Every marathon decision ID — batch 1 (01, 02, 03, 04, 05, 07, 08, 09, 33, 34, 35, 37, 38, 39, 40, 41), batch 2 (11, 12, 13, 14, 15, 16, 19, 24, 25, 28, 29, 45, 46, 49), batch 3 (06, 17, 18, 20, 21, 22, 23, 26, 27, 30, 31, 32, 36, 42, 43, 44, 47, 48, 50) — carries `RESOLVED` in `docs/DECISIONS.md`, dated 2026-07-25, Approver: Dave.
- **12/12 Phase I gating list: RESOLVED.** D-IMPL-01, 02, 03, 04, 05, 11, 14, 17, 20, 24, 26, 28 — all individually confirmed `RESOLVED` (none provisional).
- **Zero D-04 deferrals across all three batches.** Dave ruled on every decision presented; no recommendation was adopted as `PROVISIONAL ... Pending Dave confirmation at D-GATE-D.`
- `grep -c 'PROVISIONAL' docs/DECISIONS.md` → **0**.

## Register

**There are ZERO provisional resolutions.** No D-IMPL entry in `docs/DECISIONS.md` carries a `PROVISIONAL` status token; the table below is intentionally empty and the D-GATE-D presentation has no provisionals to confirm.

| D-IMPL ID | Adopted recommendation (one line) | Date |
| --- | --- | --- |
| — (none) | — | — |

## Notes

- **D-IMPL-10 (repo shape)** is recorded as "Provisionally resolved as monorepo" per CLAUDE.md §2.2 (logged 2026-07-24). This is a CLAUDE.md-governed provisional predating and outside the marathon protocol — not a D-04 deferral and not a `PROVISIONAL` status token; its remaining open sub-question (post-v0 adapter package split) is explicitly deferred scope, not a gate item.
- **D-IMPL-51** (live MongoDB metadata query) is RESOLVED and excluded from the 49-ID marathon census by design (02-RESEARCH.md decision census).

Total provisionals: 0
