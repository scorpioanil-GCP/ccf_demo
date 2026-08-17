# `s1-00-multifile` — HW-1's Control Plane documents, frozen

These nine documents are `examples/s1-00-companies-over-revenue`'s
Control Plane configuration exactly as committed at the moment HW-1
converted to the single-file `ccf_config.yaml` form (`D-IMPL-136`'s
AMENDMENT of 2026-08-15, executed by plan `16-31`). The commit that froze
them is `16-31`'s Task 1 commit — see this repository's `git log` for the
exact hash; it is named again in that commit's own message.

**Why this directory exists.** `tests/examples/test_s1_00_config_equivalence.py`
(plan `16-30`) proves `D-IMPL-136`'s content-address equivalence claim by
comparing HW-1's real, committed multi-file documents against a
hand-authored single-file fixture. That proof does not depend on the
converted example for its multi-file side — Dave's requirement, verbatim:
the equivalence fixture *"does not rely on the converted example for that
job."* Before `16-31` deleted the nine documents from `examples/`, this
directory received a copy of them, and the test was repointed at this
directory before the deletion happened — so the proof kept both sides
throughout the conversion, with no window where one side was missing.

**`backends.yaml` is absent, deliberately.** It was never part of HW-1's
manifest (`manifest.yaml` names eight artifacts; `backends.yaml` is not
one of them) and it is not part of this equivalence proof.

**These documents are not updated when HW-1 changes.** A fixture that
tracks its subject proves nothing — the whole point of freezing this
directory is that it is independent of `examples/s1-00-companies-over-revenue`,
which no longer carries these documents at all. If HW-1's *behavior*
changes later, that is a new deployment; it does not travel back into this
directory, and no future plan should edit these files to match it. A
divergence between this directory and current CCF mechanism is a signal
that the equivalence proof itself needs new material, not that these nine
files need editing.
