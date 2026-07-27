"""Decision Replay — the five-dimension record and the serve path that writes it.

Whitepaper §7.10 (INV-CH7-79 through INV-CH7-91); DESIGN.md §2B.5.

Every decision is forensically reconstructible years later against the exact
fabric state at decision time — *enforced at assembly time and at every Context
Product boundary, never bolted on*. The two modules split along that sentence:
:mod:`ccf.replay.record` declares what is recorded, and
:mod:`ccf.replay.serve` makes the recording the thing that unlocks delivery.

I.1 records Mode 1 decisions (pure algorithmic, no model invoked anywhere).
The HITL, workflow, agent-version and skill-set extensions to dimensions 2 and
4 arrive with their own pillars in I.2/I.4; the harness-attributable extension
to dimension 3 arrives in I.3 (D-25, CLAUDE.md §7.3 seam 4). The record shape is
designed to extend rather than to be replaced (INV-CH7-88 — modes and extensions
extend the five-dimension baseline, never modify it), and every one of those
extensions is a named sub-structure *inside* an existing dimension:
:class:`~ccf.replay.record.DecisionReplayRecord` has five top-level fields and
gains no sixth (INV-CH7-80).

Algorithmic package (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
