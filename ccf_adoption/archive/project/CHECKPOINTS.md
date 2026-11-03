# Checkpoint & Approval Protocol

## Purpose

Checkpoints exist to prevent large amounts of polished work from accumulating on top of an unapproved assumption. They are architectural and product-control gates, not ceremonial status updates.

## Allowed checkpoint states

Every checkpoint ends in exactly one of these states:

- **APPROVED** — proceed without required changes.
- **APPROVED WITH AMENDMENTS** — proceed after recording the specified amendments; no second approval is required unless the amendment materially changes the agreed design.
- **REVISE** — do not proceed beyond the gate; update the checkpoint artifacts and resubmit.
- **BLOCKED BY SOURCE** — authoritative evidence is missing, contradictory, or unresolved; record the blocker and stop the affected work until resolved.

## Architecture authority

David Castillo is the architecture owner and final decision authority for CCF adoption content where source evidence does not resolve an architectural or semantic question.

ChatGPT Work may recommend a disposition, but it must not silently manufacture an authoritative decision.

## Repository discipline

- Work for each major phase should occur on a dedicated `ccf_adoption` branch whenever practical.
- Internal checkpoint commits may accumulate on the same phase branch.
- A phase branch is not promoted to `main` until its phase checkpoint is approved.
- Promotion must be a non-destructive fast-forward or reviewed merge; never force-push `main` to bypass concurrent work.
- The four source repositories remain read-only regardless of available connector permissions.

## Complex-phase checkpoint rule

A complex phase must stop at its declared internal checkpoints before scaling a pattern broadly.

Examples:

- Do not design the full portal before information architecture is approved.
- Do not implement the full visual system before a visual direction is selected.
- Do not write all SDK tutorials before the consumer/assembler learning model is validated.
- Do not scale all financial-services pages before one flagship use case is approved.
- Do not publish a vulnerability-results section before assessment scope and publication posture are approved.

## Checkpoint record

Each phase checkpoint should be recorded in `ccf_adoption` using a compact record with at least:

```yaml
checkpoint: 2B
name: Visual Direction Selection
status: APPROVED
approved_by: David Castillo
date: YYYY-MM-DD
branch: phase-2-product-ux
commit: <sha>
source_snapshots:
  ccf: <sha>
  obsidian-vault: <sha>
  ccf_dataprep: <sha>
  ccf_code: <sha>
notes:
  - <material decision or amendment>
```

The source snapshot fields may be omitted when a checkpoint does not depend on a source repository, but they are strongly preferred for evidence-heavy phases.

## Conflict escalation

A checkpoint must stop as `BLOCKED BY SOURCE` when a conflict changes technical meaning and cannot be resolved from authoritative evidence. The checkpoint record should identify:

- conflicting claims;
- repository/file/commit for each claim;
- likely class of defect or drift;
- affected adoption artifacts;
- recommended disposition;
- the decision required from the architecture owner.

## What approval means

Approval means the pattern is stable enough to scale. It does not mean the artifact can never change. Later source drift, SDK changes, security findings, or architecture decisions may reopen an approved artifact; when that happens, the change should identify which earlier checkpoint assumptions are affected.

## Final release gate

No release is considered authoritative until Checkpoint 9 is **APPROVED**. The release gate should have evidence that the site is coherent, technically aligned, reproducible where promised, source-traceable, security-status-aware, and usable by the intended audiences.
