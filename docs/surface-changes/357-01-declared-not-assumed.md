# 357-01 — declared, not assumed: the wave-1 record of what the surface did and did not do

`D-IMPL-357` (wave 1 of the v1.0.2 security remediation; design accepted at
`D-IMPL-356`, `docs/superpowers/specs/2026-09-25-v1-0-2-security-remediation-design.md`).
Four lanes, thirteen tasks, joined onto one candidate. This fragment is the
wave-level record; every individual surface this wave added or reshaped is
claimed by its own per-task fragment (`357-A1`, `357-A4`, `357-B1`, `357-C1`,
`357-C4`), and none is claimed here twice.

**This fragment's prose does not reach `docs/SURFACE-CHANGES.md`.** The
assembler emits only sections carrying one of the seven field names, which was
measured twice independently during this wave: six distinctive phrases from the
residual ledger in `350-01` appear zero times in the assembled document while
present in the fragment. That is a property of the assembler, not an omission
here, and it is stated rather than left for a reader to discover — an adopter
reading the assembled log is reading the field entries, not the narrative.

## What did NOT change, stated first

- **No action id changed value, and no handle signature changed.** The wave
  added one audit action and one closed audit vocabulary (`357-A4`); every
  existing action id, capability name and handle signature is byte-identical to
  the wave base.
- **No HTTP wire changed.** The resumption endpoint takes the same body and
  returns the same shapes; what changed is which bodies it refuses. A caller
  that was correct before is correct now.
- **No historical replay byte or content address was rewritten.** The new
  replay fields are hash-transparent at the sentinel, so a pre-wave record
  rehydrates to the same address. `gate_routes` is marked as a generation
  boundary rather than transparent, so content hashes for workflow definitions
  DO move — by design, and the migration entry in `357-A1` says so.
- **Nothing under `examples/` or `archive/` was modified.** They are frozen
  specimens (`D-IMPL-261`). Where a shipped example is now refused by a new
  check, that is SDK evidence and is ledgered — see `SEC353-G-09`, and the
  three examples named in `357-C1`'s migration note.
- **No clock was read.** The fabric clock is wave 2's subject; this wave
  contains no `datetime.now`, `utcnow` or `time.time` in any changed line.
- **No SDK default temporal window was introduced**, and no tenant window was
  assumed where none is declared.
- **The mechanism floor's grammar, its covered surface and its call site are
  code-identical across the whole of lane C after the floor landed**, proved by
  abstract-syntax comparison with docstrings stripped at every commit. The
  adopter-declarable grammar added later narrows beneath it and cannot widen
  past it.

## What remains open, and is named rather than implied

- **The concurrency window.** A verdict recorded during a resumption's own
  read-decide-commit window is not seen. This and the concurrent-resume double
  passage are ONE residual — the absence of atomicity around that sequence —
  and a lock or compare-and-set that covers the conflict population as well as
  the state record closes both. A guarantee over the state record alone closes
  only the second. `350-01` carries the ledger.
- **The floor reads declared positions.** Several request fields, values the
  resolution stage supplies, and strings at positions the declaration does not
  type as strings are not judged. `357-C1`'s entry names each carrier.
- **An invisible-character identity still mints a node**, because the language's
  own definition of whitespace does not include it. Ruled to stay as it is;
  disclosed, not fixed.
- **The registration-time grammar check couples to two private standard-library
  modules.** A language upgrade can move them. Belongs on the release checklist.
- **The assembled change document is not a complete security ledger.** The
  assembler silently truncated bare bullets; the two clauses this wave shipped
  as fragments are repaired and a check-mode refusal now makes a truncation a
  red build, but the remaining entries are unswept and get their own decision id.
